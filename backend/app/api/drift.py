"""Drift API routes."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from app.models.schemas import DriftResult
from app.engines.drift import DriftEngine

router = APIRouter()


class DriftRequest(BaseModel):
    lat: float
    lon: float
    detection_time: str
    max_hours: float = 48.0
    current_speed_kn: float = 0.3
    current_direction_deg: float = 45.0
    wind_speed_ms: float = 5.0
    wind_direction_deg: float = 270.0


@router.post("/backward", response_model=DriftResult)
async def drift_backward(req: DriftRequest):
    """Trace backward to estimate spill origin."""
    engine = DriftEngine(
        current_speed_kn=req.current_speed_kn,
        current_direction_deg=req.current_direction_deg,
        wind_speed_ms=req.wind_speed_ms,
        wind_direction_deg=req.wind_direction_deg,
    )
    return engine.trace_backward(req.lat, req.lon, req.detection_time, req.max_hours)


@router.post("/forward", response_model=DriftResult)
async def drift_forward(req: DriftRequest):
    """Predict forward spill trajectory."""
    engine = DriftEngine(
        current_speed_kn=req.current_speed_kn,
        current_direction_deg=req.current_direction_deg,
        wind_speed_ms=req.wind_speed_ms,
        wind_direction_deg=req.wind_direction_deg,
    )
    return engine.trace_forward(req.lat, req.lon, req.detection_time, req.max_hours)
