"""AIS API routes."""

from fastapi import APIRouter

from app.models.schemas import AisPosition, VesselTrack, AisGap
from app.engines.ais_engine import AISIngestionEngine

router = APIRouter()
engine = AISIngestionEngine()


@router.post("/ingest")
async def ingest_positions(positions: list[AisPosition]):
    """Ingest a batch of AIS positions."""
    engine.ingest(positions)
    return {"status": "ok", "vessels_tracked": len(engine.positions)}


@router.get("/tracks", response_model=list[VesselTrack])
async def get_tracks():
    """Get all vessel tracks."""
    return engine.build_tracks()


@router.get("/gaps", response_model=list[AisGap])
async def get_gaps():
    """Get all detected AIS gaps across all tracks."""
    return engine.get_all_gaps()
