"""
Simplified Drift Engine.
Lagrangian advection model for oil spill trajectory estimation.
  displacement = (current_vector + 0.03 * wind_vector) * dt

This is a deliberately simplified model — a path to full OpenDrift/HYCOM
integration is documented but not implemented here.
"""

import math
from datetime import datetime, timedelta
from typing import Optional

from app.models.schemas import DriftResult, DriftPoint


# ── Default environmental parameters ───────────────────────────────

WIND_FACTOR = 0.03  # Standard wind drift factor for surface oil slicks
DEFAULT_CURRENT_SPEED_KN = 0.3  # Typical surface current ~0.3 knots
DEFAULT_CURRENT_DIRECTION_DEG = 45  # Northeast (configurable per incident)
DEFAULT_WIND_SPEED_MS = 5.0
DEFAULT_WIND_DIRECTION_DEG = 270  # West wind (blows east)
STEP_HOURS = 1.0


def _vector_from_speed_direction(speed: float, direction_deg: float) -> tuple[float, float]:
    """Convert speed + direction to (east, north) velocity in km/h."""
    direction_rad = math.radians(direction_deg)
    # direction = where it's going TO (meteorological: where wind comes FROM is convention, but we use "toward")
    east = speed * math.sin(direction_rad)
    north = speed * math.cos(direction_rad)
    return east, north


def _step_position(
    lat: float, lon: float,
    current_east_kmh: float, current_north_kmh: float,
    wind_east_kmh: float, wind_north_kmh: float,
    dt_hours: float,
    direction: int = 1,  # +1 = forward, -1 = backward
) -> tuple[float, float]:
    """Advance one Lagrangian step."""
    R = 6371.0
    # Total displacement
    d_east = (current_east_kmh + WIND_FACTOR * wind_east_kmh) * dt_hours * direction
    d_north = (current_north_kmh + WIND_FACTOR * wind_north_kmh) * dt_hours * direction

    # Convert km to lat/lon delta
    d_lat = (d_north / R) * (180 / math.pi)
    d_lon = (d_east / (R * math.cos(math.radians(lat)))) * (180 / math.pi)

    return lat + d_lat, lon + d_lon


class DriftEngine:
    """Runs simplified oil spill drift estimation backward and forward."""

    def __init__(
        self,
        current_speed_kn: float = DEFAULT_CURRENT_SPEED_KN,
        current_direction_deg: float = DEFAULT_CURRENT_DIRECTION_DEG,
        wind_speed_ms: float = DEFAULT_WIND_SPEED_MS,
        wind_direction_deg: float = DEFAULT_WIND_DIRECTION_DEG,
    ):
        # Convert current: knots → km/h (1 kn = 1.852 km/h)
        self.current_east_kmh, self.current_north_kmh = _vector_from_speed_direction(
            current_speed_kn * 1.852, current_direction_deg
        )
        # Convert wind: m/s → km/h (1 m/s = 3.6 km/h)
        self.wind_east_kmh, self.wind_north_kmh = _vector_from_speed_direction(
            wind_speed_ms * 3.6, wind_direction_deg
        )

    def trace_backward(
        self,
        spill_lat: float,
        spill_lon: float,
        detection_time: str,
        max_hours: float = 48.0,
    ) -> DriftResult:
        """
        Trace backward from detected spill location to estimate origin.
        Returns the trajectory and estimated origin point.
        """
        t = datetime.fromisoformat(detection_time)
        trajectory = []
        lat, lon = spill_lat, spill_lon

        steps = int(max_hours / STEP_HOURS)
        for i in range(steps):
            lat, lon = _step_position(
                lat, lon,
                self.current_east_kmh, self.current_north_kmh,
                self.wind_east_kmh, self.wind_north_kmh,
                STEP_HOURS,
                direction=-1,  # backward
            )
            t = t - timedelta(hours=STEP_HOURS)
            trajectory.append(DriftPoint(
                lat=round(lat, 6),
                lon=round(lon, 6),
                timestamp=t.isoformat(),
                step_hours=round((i + 1) * STEP_HOURS, 1),
            ))

        # The first step back is the most likely origin
        if trajectory:
            origin = trajectory[0]
            return DriftResult(
                origin_lat=origin.lat,
                origin_lon=origin.lon,
                origin_time=origin.timestamp,
                trajectory=list(reversed(trajectory)),  # chronological: origin → detection
            )

        return DriftResult(
            origin_lat=spill_lat,
            origin_lon=spill_lon,
            origin_time=detection_time,
            trajectory=[],
        )

    def trace_forward(
        self,
        spill_lat: float,
        spill_lon: float,
        detection_time: str,
        max_hours: float = 48.0,
    ) -> DriftResult:
        """
        Forward prediction: where will the slick be at +6h, +24h, +48h?
        """
        t = datetime.fromisoformat(detection_time)
        trajectory = []
        lat, lon = spill_lat, spill_lon

        steps = int(max_hours / STEP_HOURS)
        for i in range(steps):
            lat, lon = _step_position(
                lat, lon,
                self.current_east_kmh, self.current_north_kmh,
                self.wind_east_kmh, self.wind_north_kmh,
                STEP_HOURS,
                direction=+1,  # forward
            )
            t = t + timedelta(hours=STEP_HOURS)
            trajectory.append(DriftPoint(
                lat=round(lat, 6),
                lon=round(lon, 6),
                timestamp=t.isoformat(),
                step_hours=round((i + 1) * STEP_HOURS, 1),
            ))

        return DriftResult(
            origin_lat=spill_lat,
            origin_lon=spill_lon,
            origin_time=detection_time,
            trajectory=trajectory,
        )
