"""Attribution API routes."""

from fastapi import APIRouter

from app.models.schemas import (
    AttributionRequest, AttributionResult, VesselTrack,
)
from app.engines.ais_engine import AISIngestionEngine
from app.engines.attribution import compute_attribution
from app.engines.drift import DriftEngine

router = APIRouter()

# Shared state for the active AIS tracks (populated via /api/demo or /api/ais/ingest)
_active_tracks: list[VesselTrack] = []


def set_tracks(tracks: list[VesselTrack]):
    global _active_tracks
    _active_tracks = tracks


@router.post("/score", response_model=AttributionResult)
async def score_attribution(req: AttributionRequest):
    """
    Score all candidate vessels against a spill.
    If no tracks loaded, returns empty.
    """
    if not _active_tracks:
        return AttributionResult(
            spill_id="UNKNOWN",
            candidates=[],
            top_suspect=None,
            origin_estimate=None,
        )

    # If origin not provided, run drift backward to estimate it
    origin_lat = req.origin_lat
    origin_lon = req.origin_lon
    origin_time = req.origin_time

    if origin_lat is None or origin_lon is None:
        drift_engine = DriftEngine()
        origin = drift_engine.trace_backward(
            req.spill_lat, req.spill_lon, req.detection_time, max_hours=req.time_window_hours
        )
        origin_lat = origin.origin_lat
        origin_lon = origin.origin_lon
        origin_time = origin.origin_time
    else:
        origin = None

    suspects = compute_attribution(
        tracks=_active_tracks,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        spill_time=req.detection_time,
        origin_time=origin_time,
    )

    return AttributionResult(
        spill_id=f"SPILL-{req.spill_lat:.2f}-{req.spill_lon:.2f}",
        candidates=suspects,
        top_suspect=suspects[0] if suspects else None,
        origin_estimate=origin,
    )


@router.get("/weights")
async def get_weights():
    """Return the current scoring weights for transparency."""
    from app.engines.attribution import WEIGHTS
    return WEIGHTS
