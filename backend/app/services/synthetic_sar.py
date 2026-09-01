"""
Synthetic SAR data generator for demo/testing.
Generates realistic-looking SAR-like images with oil spills, look-alikes, ships, and land.
"""

import numpy as np
from PIL import Image
import io
import base64
import uuid


def generate_sar_tile(
    size: int = 256,
    spill_center: tuple[int, int] | None = None,
    include_look_alike: bool = True,
    include_ship: bool = True,
    include_land: bool = False,
    noise_level: float = 0.15,
    seed: int | None = None,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Generate a synthetic SAR-like image with pixel-level ground truth mask.

    Returns:
        (sar_image, mask, metadata)
        - sar_image: uint8 array (H, W) — simulated SAR backscatter
        - mask: uint8 array (H, W) — class labels (0=sea, 1=oil, 2=look-alike, 3=ship, 4=land)
        - metadata: dict with info about placed features
    """
    rng = np.random.default_rng(seed)
    meta = {"features": []}

    # ── Base sea surface with speckle noise ──
    sea_base = 140 + rng.normal(0, noise_level * 40, (size, size))
    # Add slight gradient (simulating varying wind/angle)
    y_grad = np.linspace(0, 15, size).reshape(-1, 1)
    sea_base += y_grad

    sar = np.clip(sea_base, 0, 255).astype(np.uint8)
    mask = np.zeros((size, size), dtype=np.uint8)  # 0 = sea surface

    # ── Oil spill (dark patch, elongated, with feathered edges) ──
    cx = spill_center[0] if spill_center else rng.integers(size // 4, 3 * size // 4)
    cy = spill_center[1] if spill_center else rng.integers(size // 4, 3 * size // 4)
    spill_length = rng.integers(40, 80)
    spill_width = rng.integers(10, 25)
    angle = rng.uniform(0, np.pi)

    yy, xx = np.mgrid[:size, :size]
    # Rotated ellipse
    cos_a, sin_a = np.cos(angle), np.sin(angle)
    rx = (xx - cx) * cos_a + (yy - cy) * sin_a
    ry = -(xx - cx) * sin_a + (yy - cy) * cos_a
    ellipse = (rx / spill_length) ** 2 + (ry / spill_width) ** 2

    # Feathered edges
    spill_mask_f = np.clip(1.0 - ellipse, 0, 1)
    spill_mask_f *= rng.uniform(0.6, 1.0)  # variable intensity
    spill_mask = spill_mask_f > 0.15

    # Oil suppresses backscatter (darkens the SAR)
    sar[spill_mask] = np.clip(sar[spill_mask].astype(float) * rng.uniform(0.25, 0.45), 10, 80).astype(np.uint8)
    mask[spill_mask] = 1  # oil spill

    meta["features"].append({
        "type": "oil_spill",
        "centroid_px": [int(cx), int(cy)],
        "angle_rad": round(float(angle), 2),
        "length_px": int(spill_length),
        "width_px": int(spill_width),
    })

    # ── Look-alike (biogenic film / low-wind zone) ──
    if include_look_alike:
        la_cx = rng.integers(20, size - 20)
        la_cy = rng.integers(20, size - 20)
        la_r = rng.integers(15, 35)
        la_mask = ((xx - la_cx) ** 2 + (yy - la_cy) ** 2) < la_r ** 2
        # Look-alikes are darker than sea but less uniform than oil
        sar[la_mask & ~spill_mask] = np.clip(
            sar[la_mask & ~spill_mask].astype(float) * rng.uniform(0.5, 0.7), 30, 120
        ).astype(np.uint8)
        mask[la_mask & ~spill_mask] = 2  # look-alike
        meta["features"].append({"type": "look_alike", "centroid_px": [int(la_cx), int(la_cy)], "radius_px": int(la_r)})

    # ── Ship (bright point target) ──
    if include_ship:
        sx, sy = rng.integers(10, size - 10, size=2)
        ship_r = rng.integers(2, 4)
        ship_mask = ((xx - sx) ** 2 + (yy - sy) ** 2) < ship_r ** 2
        sar[ship_mask] = rng.integers(220, 255)
        mask[ship_mask] = 3  # ship
        meta["features"].append({"type": "ship", "centroid_px": [int(sx), int(sy)]})

    # ── Land (optional, corner) ──
    if include_land:
        land_mask = (xx < size // 5) & (yy < size // 5)
        sar[land_mask] = rng.integers(180, 230, size=land_mask.sum())
        mask[land_mask] = 4  # land
        meta["features"].append({"type": "land", "region": "top-left"})

    # Final speckle noise pass
    speckle = rng.normal(1.0, noise_level * 0.3, (size, size))
    sar = np.clip(sar.astype(float) * speckle, 0, 255).astype(np.uint8)

    return sar, mask, meta


def sar_to_base64(sar: np.ndarray) -> str:
    """Convert SAR array to base64-encoded PNG."""
    img = Image.fromarray(sar, mode="L")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def generate_batch(n: int = 12, size: int = 256) -> list[dict]:
    """Generate a batch of synthetic SAR tiles with metadata."""
    tiles = []
    for i in range(n):
        seed = 42 + i
        sar, mask, meta = generate_sar_tile(
            size=size,
            include_look_alike=(i % 3 != 0),  # 2/3 have look-alikes
            include_ship=True,
            include_land=(i % 4 == 0),
            seed=seed,
        )
        tiles.append({
            "id": str(uuid.uuid4()),
            "sar_b64": sar_to_base64(sar),
            "mask": mask.tolist(),
            "metadata": meta,
            "size": size,
        })
    return tiles
