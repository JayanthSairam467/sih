"""Detection API routes."""

from fastapi import APIRouter, UploadFile, File
import numpy as np

from app.models.schemas import DetectionRequest, DetectionResult
from app.engines.detection import DetectionEngine
from app.services.synthetic_sar import generate_sar_tile, generate_batch

router = APIRouter()
engine = DetectionEngine()


@router.post("/detect", response_model=DetectionResult)
async def detect_spill(req: DetectionRequest):
    """Run oil spill detection on a SAR tile."""
    if req.image_b64:
        # TODO: decode base64 → numpy array
        pass
    # For demo: generate synthetic SAR at the given location
    sar, mask, meta = generate_sar_tile(
        size=256,
        spill_center=(128, 128),
        seed=42,
    )
    result = engine.detect(sar, req.lat, req.lon, req.timestamp)
    return result


@router.api_route("/detect-synthetic", methods=["GET", "POST"])
async def detect_synthetic(lat: float = 21.5, lon: float = 39.1):
    """Generate and detect on a synthetic SAR tile."""
    from datetime import datetime
    sar, mask, meta = generate_sar_tile(size=256, spill_center=(128, 128), seed=42)
    result = engine.detect(sar, lat, lon, datetime.now().isoformat())
    return {"detection": result, "source_metadata": meta}


@router.get("/samples")
async def get_samples(n: int = 12):
    """Generate a batch of synthetic SAR samples."""
    return {"samples": generate_batch(n=n)}
