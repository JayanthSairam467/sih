"""Pydantic schemas for API request/response models."""

from pydantic import BaseModel, Field
from typing import Optional
import enum


# ── Enums ──────────────────────────────────────────────────────────

class ConfidenceLevel(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class SARClass(str, enum.Enum):
    SEA_SURFACE = "sea_surface"
    OIL_SPILL = "oil_spill"
    LOOK_ALIKE = "look_alike"
    SHIP = "ship"
    LAND = "land"


# ── Detection ──────────────────────────────────────────────────────

class DetectionResult(BaseModel):
    spill_id: str
    centroid_lat: float
    centroid_lon: float
    area_km2: float
    confidence: ConfidenceLevel
    classes_found: dict[str, int] = Field(description="Pixel count per class")
    bbox: list[float] = Field(description="[min_lon, min_lat, max_lon, max_lat]")
    mask_rle: Optional[str] = Field(default=None, description="Run-length encoded mask for frontend overlay")


class DetectionRequest(BaseModel):
    image_b64: Optional[str] = Field(default=None, description="Base64-encoded SAR tile")
    lat: float
    lon: float
    timestamp: str
    source: str = "synthetic"


# ── AIS ────────────────────────────────────────────────────────────

class AisPosition(BaseModel):
    mmsi: str
    lat: float
    lon: float
    timestamp: str
    speed_knots: float
    course_deg: float
    heading: Optional[float] = None
    vessel_name: Optional[str] = None
    vessel_type: Optional[str] = None
    imo: Optional[str] = None


class AisGap(BaseModel):
    mmsi: str
    vessel_name: Optional[str]
    gap_start: str
    gap_end: str
    gap_duration_hours: float
    last_known_lat: float
    last_known_lon: float
    resume_lat: float
    resume_lon: float


class VesselTrack(BaseModel):
    mmsi: str
    vessel_name: Optional[str]
    vessel_type: Optional[str]
    positions: list[AisPosition]
    gaps: list[AisGap]


# ── Drift ──────────────────────────────────────────────────────────

class DriftPoint(BaseModel):
    lat: float
    lon: float
    timestamp: str
    step_hours: float


class DriftResult(BaseModel):
    origin_lat: float
    origin_lon: float
    origin_time: str
    trajectory: list[DriftPoint]
    model_label: str = "Simplified Lagrangian advection (wind factor 0.03)"


# ── Attribution ────────────────────────────────────────────────────

class ScoreBreakdown(BaseModel):
    component: str
    raw_value: float
    weight: float
    weighted_value: float
    explanation: str


class VesselSuspect(BaseModel):
    mmsi: str
    vessel_name: Optional[str]
    vessel_type: Optional[str]
    composite_score: float
    confidence: ConfidenceLevel
    score_breakdown: list[ScoreBreakdown]
    has_ais_gap: bool
    track_summary: Optional[str] = None


class AttributionRequest(BaseModel):
    spill_lat: float
    spill_lon: float
    detection_time: str
    origin_lat: Optional[float] = None
    origin_lon: Optional[float] = None
    origin_time: Optional[str] = None
    area_radius_km: float = 50.0
    time_window_hours: float = 24.0


class AttributionResult(BaseModel):
    spill_id: str
    candidates: list[VesselSuspect]
    top_suspect: Optional[VesselSuspect]
    origin_estimate: DriftResult


# ── Demo ───────────────────────────────────────────────────────────

class IncidentInfo(BaseModel):
    id: str
    name: str
    date: str
    description: str
    location: str
    lat: float
    lon: float


class IncidentResponse(BaseModel):
    incident: IncidentInfo
    detection: DetectionResult
    vessel_tracks: list[VesselTrack]
    attribution: AttributionResult
    drift_forward: DriftResult
    drift_backward: DriftResult
