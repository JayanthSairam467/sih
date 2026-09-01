"""
Spill Detection Engine.
Uses a lightweight U-Net for SAR image segmentation.
For the college round: synthetic data + simplified model.
For actual SIH: swap to real Krestenitis dataset + pretrained checkpoint.

Torch is imported lazily — the numpy fallback path is used for demo/fast startup.
"""

import numpy as np
from typing import Optional
import uuid

from app.models.schemas import DetectionResult, ConfidenceLevel


# ── Class definitions ──────────────────────────────────────────────

CLASS_NAMES = {0: "sea_surface", 1: "oil_spill", 2: "look_alike", 3: "ship", 4: "land"}
OIL_CLASS = 1
LOOK_ALIKE_CLASS = 2
SHIP_CLASS = 3
LAND_CLASS = 4


def _get_torch():
    """Lazy torch import."""
    import torch
    return torch


class DetectionEngine:
    """Manages the detection model and inference."""

    def __init__(self):
        self.model = None
        self._use_torch = False
        self._loaded = False

    def _init_torch_model(self):
        """Try to initialize the PyTorch model."""
        try:
            torch = _get_torch()
            import torch.nn as nn

            class DoubleConv(nn.Module):
                def __init__(self, in_ch, out_ch):
                    super().__init__()
                    self.conv = nn.Sequential(
                        nn.Conv2d(in_ch, out_ch, 3, padding=1),
                        nn.BatchNorm2d(out_ch),
                        nn.ReLU(inplace=True),
                        nn.Conv2d(out_ch, out_ch, 3, padding=1),
                        nn.BatchNorm2d(out_ch),
                        nn.ReLU(inplace=True),
                    )

                def forward(self, x):
                    return self.conv(x)

            class MiniUNet(nn.Module):
                def __init__(self, n_classes=5, in_channels=1):
                    super().__init__()
                    self.enc1 = DoubleConv(in_channels, 32)
                    self.enc2 = DoubleConv(32, 64)
                    self.enc3 = DoubleConv(64, 128)
                    self.pool = nn.MaxPool2d(2)
                    self.bottleneck = DoubleConv(128, 256)
                    self.up3 = nn.ConvTranspose2d(256, 128, 2, stride=2)
                    self.dec3 = DoubleConv(256, 128)
                    self.up2 = nn.ConvTranspose2d(128, 64, 2, stride=2)
                    self.dec2 = DoubleConv(128, 64)
                    self.up1 = nn.ConvTranspose2d(64, 32, 2, stride=2)
                    self.dec1 = DoubleConv(64, 32)
                    self.out = nn.Conv2d(32, n_classes, 1)

                def forward(self, x):
                    e1 = self.enc1(x)
                    e2 = self.enc2(self.pool(e1))
                    e3 = self.enc3(self.pool(e2))
                    b = self.bottleneck(self.pool(e3))
                    d3 = self.dec3(torch.cat([self.up3(b), e3], dim=1))
                    d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
                    d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
                    return self.out(d1)

            self.model = MiniUNet(n_classes=5, in_channels=1)
            self.model.eval()
            self._use_torch = True
            self._torch = torch
        except Exception:
            self._use_torch = False

    def _detect_numpy(self, sar_array: np.ndarray) -> np.ndarray:
        """
        Numpy-based SAR analysis: threshold oil-like dark pixels,
        separate by shape/texture heuristics.
        """
        h, w = sar_array.shape
        mask = np.zeros((h, w), dtype=np.uint8)

        # Sea surface: median brightness
        sea_median = np.median(sar_array)

        # Oil spills: significantly darker than surroundings (sharp drop in backscatter)
        # Use adaptive thresholding: pixels < 40% of local mean are likely oil
        from scipy.ndimage import uniform_filter
        local_mean = uniform_filter(sar_array.astype(float), size=20)
        dark_ratio = sar_array.astype(float) / (local_mean + 1)

        # Oil: very dark relative to local surroundings
        oil_mask = dark_ratio < 0.45
        # Look-alike: somewhat dark but less so, often larger/rounder
        la_mask = (dark_ratio >= 0.45) & (dark_ratio < 0.65) & (local_mean < sea_median * 0.9)

        # Ship: bright point targets
        ship_mask = sar_array > 220

        mask[oil_mask] = OIL_CLASS
        mask[la_mask & ~oil_mask] = LOOK_ALIKE_CLASS
        mask[ship_mask & ~oil_mask & ~la_mask] = SHIP_CLASS

        return mask

    def load_checkpoint(self, path: Optional[str] = None):
        """Load a trained checkpoint. Falls back to numpy if torch unavailable."""
        self._init_torch_model()
        if self.model and path:
            self._torch.load_state_dict(self._torch.load(path, map_location="cpu"))
        self._loaded = True

    def detect(self, sar_array: np.ndarray, lat: float, lon: float, timestamp: str) -> DetectionResult:
        """
        Run detection on a SAR tile (H, W) uint8 array.
        Returns DetectionResult with polygon, confidence, and class breakdown.
        """
        if not self._loaded:
            self.load_checkpoint()

        h, w = sar_array.shape

        if self._use_torch and self.model:
            # PyTorch path
            torch = self._torch
            inp = torch.from_numpy(sar_array.astype(np.float32) / 255.0).unsqueeze(0).unsqueeze(0)
            with torch.no_grad():
                logits = self.model(inp)
                probs = torch.softmax(logits, dim=1)
                pred_mask = torch.argmax(probs, dim=1).squeeze().numpy().astype(np.uint8)
        else:
            # Numpy fallback
            try:
                pred_mask = self._detect_numpy(sar_array)
            except ImportError:
                # No scipy either — do simple global thresholding
                pred_mask = np.zeros_like(sar_array)
                threshold = np.percentile(sar_array, 15)
                pred_mask[sar_array < threshold] = OIL_CLASS
                bright = np.percentile(sar_array, 98)
                pred_mask[(sar_array > bright)] = SHIP_CLASS

        # Class counts
        class_counts = {}
        for cls_id, cls_name in CLASS_NAMES.items():
            count = int((pred_mask == cls_id).sum())
            class_counts[cls_name] = count

        oil_mask = (pred_mask == OIL_CLASS)
        oil_pixels = np.argwhere(oil_mask)

        if len(oil_pixels) > 0:
            centroid_yx = oil_pixels.mean(axis=0)
            area_km2 = len(oil_pixels) * (10 * 10) / 1e6

            min_y, min_x = oil_pixels.min(axis=0)
            max_y, max_x = oil_pixels.max(axis=0)
            bbox = [
                lon + (min_x / w - 0.5) * 0.1,
                lat + (min_y / h - 0.5) * 0.1,
                lon + (max_x / w - 0.5) * 0.1,
                lat + (max_y / h - 0.5) * 0.1,
            ]

            c_lat = lat + (centroid_yx[0] / h - 0.5) * 0.1
            c_lon = lon + (centroid_yx[1] / w - 0.5) * 0.1

            oil_ratio = class_counts.get("oil_spill", 0) / max(sum(class_counts.values()), 1)
            la_ratio = class_counts.get("look_alike", 0) / max(sum(class_counts.values()), 1)

            if oil_ratio > 0.15 and la_ratio < 0.05:
                confidence = ConfidenceLevel.CRITICAL
            elif oil_ratio > 0.08:
                confidence = ConfidenceLevel.HIGH
            elif oil_ratio > 0.03:
                confidence = ConfidenceLevel.MEDIUM
            else:
                confidence = ConfidenceLevel.LOW
        else:
            c_lat, c_lon = lat, lon
            area_km2 = 0.0
            bbox = [lon, lat, lon, lat]
            confidence = ConfidenceLevel.LOW

        spill_id = f"SPILL-{uuid.uuid4().hex[:8].upper()}"

        return DetectionResult(
            spill_id=spill_id,
            centroid_lat=round(c_lat, 6),
            centroid_lon=round(c_lon, 6),
            area_km2=round(area_km2, 4),
            confidence=confidence,
            classes_found=class_counts,
            bbox=[round(b, 6) for b in bbox],
        )
