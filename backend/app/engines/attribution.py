"""
Attribution Scoring Engine.
Implements the 5-component composite scoring formula:

  composite_score(vessel) =
      w1 * spatial_proximity_score(vessel_track, drift_origin)
    + w2 * temporal_fit_score(vessel_presence_window, spill_time_window)
    + w3 * ais_gap_bonus(vessel)
    + w4 * course_speed_anomaly_score(vessel_track)
    + w5 * vessel_type_prior(vessel_type)

Every component is tracked and returned for UI transparency.
"""

import math
from datetime import datetime, timedelta
from typing import Optional

from app.models.schemas import (
    VesselSuspect, ScoreBreakdown, ConfidenceLevel,
    VesselTrack, DriftResult,
)
from app.engines.ais_engine import haversine_km, VESSEL_TYPE_PRIORS


# ── Weights ────────────────────────────────────────────────────────

WEIGHTS = {
    "spatial_proximity": 0.30,
    "temporal_fit": 0.25,
    "ais_gap": 0.20,
    "course_speed_anomaly": 0.15,
    "vessel_type_prior": 0.10,
}


# ── Individual scoring functions ───────────────────────────────────

def spatial_proximity_score(
    vessel_track: VesselTrack,
    origin_lat: float,
    origin_lon: float,
    max_distance_km: float = 100.0,
) -> float:
    """
    Score based on closest point of vessel track to estimated spill origin.
    Returns 0.0–1.0. Closer = higher.
    """
    min_dist = float("inf")
    for pos in vessel_track.positions:
        d = haversine_km(pos.lat, pos.lon, origin_lat, origin_lon)
        min_dist = min(min_dist, d)

    if min_dist >= max_distance_km:
        return 0.0
    return max(0.0, 1.0 - (min_dist / max_distance_km))


def temporal_fit_score(
    vessel_track: VesselTrack,
    spill_time: str,
    window_hours: float = 24.0,
) -> float:
    """
    Score based on whether the vessel was present during the spill window.
    Returns 0.0–1.0. Better overlap = higher.
    """
    spill_t = datetime.fromisoformat(spill_time)
    window_start = spill_t - timedelta(hours=window_hours / 2)
    window_end = spill_t + timedelta(hours=window_hours / 2)

    overlap_seconds = 0
    for i, pos in enumerate(vessel_track.positions):
        pos_t = datetime.fromisoformat(pos.timestamp)
        if window_start <= pos_t <= window_end:
            # Count time overlap (approximate with inter-sample interval)
            if i + 1 < len(vessel_track.positions):
                next_t = datetime.fromisoformat(vessel_track.positions[i + 1].timestamp)
                dt = min(next_t, window_end) - max(pos_t, window_start)
                overlap_seconds += max(0, dt.total_seconds())
            else:
                overlap_seconds += 1800  # Assume 30-min reporting interval

    total_window = (window_end - window_start).total_seconds()
    return min(1.0, overlap_seconds / max(total_window, 1))


def ais_gap_bonus(
    vessel_track: VesselTrack,
    spill_time: str,
    origin_lat: float,
    origin_lon: float,
    window_hours: float = 24.0,
    proximity_km: float = 30.0,
) -> float:
    """
    Large bonus if vessel went AIS-dark during a window that overlaps
    the spill's estimated origin time AND is near the origin location.
    Returns 0.0–1.0. This is the key dark-vessel feature.
    """
    spill_t = datetime.fromisoformat(spill_time)

    for gap in vessel_track.gaps:
        gap_start = datetime.fromisoformat(gap.gap_start)
        gap_end = datetime.fromisoformat(gap.gap_end)

        # Check temporal overlap with spill window
        window_start = spill_t - timedelta(hours=window_hours / 2)
        window_end = spill_t + timedelta(hours=window_hours / 2)

        if gap_end < window_start or gap_start > window_end:
            continue  # No temporal overlap

        # Check spatial proximity — gap's last known position near origin
        dist = haversine_km(gap.last_known_lat, gap.last_known_lon, origin_lat, origin_lon)
        if dist > proximity_km:
            continue  # Too far

        # Gap overlaps temporally AND is spatially relevant
        # Longer gaps near the origin = higher bonus
        duration_score = min(1.0, gap.gap_duration_hours / 12.0)  # Max out at 12h gap
        proximity_score = max(0.0, 1.0 - dist / proximity_km)

        return 0.5 * duration_score + 0.5 * proximity_score

    return 0.0


def course_speed_anomaly_score(
    vessel_track: VesselTrack,
    spill_time: str,
    window_hours: float = 6.0,
) -> float:
    """
    Detect sudden slowdown or course change near the spill time —
    indicative of discharging (vessel slows to release oil).
    Returns 0.0–1.0.
    """
    if len(vessel_track.positions) < 3:
        return 0.0

    spill_t = datetime.fromisoformat(spill_time)
    window_start = spill_t - timedelta(hours=window_hours)
    window_end = spill_t + timedelta(hours=window_hours)

    # Filter positions in window
    in_window = [
        p for p in vessel_track.positions
        if window_start <= datetime.fromisoformat(p.timestamp) <= window_end
    ]
    if len(in_window) < 3:
        return 0.0

    # Check for speed drops
    speeds = [p.speed_knots for p in in_window]
    avg_speed = sum(speeds) / len(speeds)
    min_speed = min(speeds)
    max_speed = max(speeds)

    speed_anomaly = 0.0
    if avg_speed > 0:
        speed_anomaly = max(0.0, (avg_speed - min_speed) / avg_speed)

    # Check for course changes
    courses = [p.course_deg for p in in_window]
    max_course_change = 0.0
    for i in range(len(courses) - 1):
        delta = abs(courses[i + 1] - courses[i])
        if delta > 180:
            delta = 360 - delta
        max_course_change = max(max_course_change, delta)

    course_anomaly = min(1.0, max_course_change / 90.0)  # 90° change = max anomaly

    return 0.6 * speed_anomaly + 0.4 * course_anomaly


def vessel_type_prior(vessel_type: Optional[str]) -> float:
    """Weak prior based on vessel type — tankers/cargo more likely to carry oil."""
    if not vessel_type:
        return VESSEL_TYPE_PRIORS.get("unknown", 0.4)
    return VESSEL_TYPE_PRIORS.get(vessel_type.lower(), VESSEL_TYPE_PRIORS["unknown"])


# ── Composite scorer ───────────────────────────────────────────────

def compute_attribution(
    tracks: list[VesselTrack],
    origin_lat: float,
    origin_lon: float,
    spill_time: str,
    origin_time: Optional[str] = None,
) -> list[VesselSuspect]:
    """
    Score all candidate vessels against a spill's estimated origin.
    Returns ranked list of suspects (highest score first).
    """
    ref_time = origin_time or spill_time
    suspects = []

    for track in tracks:
        # Compute each component
        s1 = spatial_proximity_score(track, origin_lat, origin_lon)
        s2 = temporal_fit_score(track, ref_time)
        s3 = ais_gap_bonus(track, spill_time, origin_lat, origin_lon)
        s4 = course_speed_anomaly_score(track, ref_time)
        s5 = vessel_type_prior(track.vessel_type)

        # Weighted composite
        composite = (
            WEIGHTS["spatial_proximity"] * s1
            + WEIGHTS["temporal_fit"] * s2
            + WEIGHTS["ais_gap"] * s3
            + WEIGHTS["course_speed_anomaly"] * s4
            + WEIGHTS["vessel_type_prior"] * s5
        )

        # Normalize to confidence level
        if composite >= 0.75:
            conf = ConfidenceLevel.CRITICAL
        elif composite >= 0.55:
            conf = ConfidenceLevel.HIGH
        elif composite >= 0.35:
            conf = ConfidenceLevel.MEDIUM
        else:
            conf = ConfidenceLevel.LOW

        breakdown = [
            ScoreBreakdown(
                component="Spatial Proximity",
                raw_value=round(s1, 4),
                weight=WEIGHTS["spatial_proximity"],
                weighted_value=round(WEIGHTS["spatial_proximity"] * s1, 4),
                explanation=f"Closest point to drift origin: {round(s1 * 100, 1)}% proximity score",
            ),
            ScoreBreakdown(
                component="Temporal Fit",
                raw_value=round(s2, 4),
                weight=WEIGHTS["temporal_fit"],
                weighted_value=round(WEIGHTS["temporal_fit"] * s2, 4),
                explanation=f"Vessel presence during spill window: {round(s2 * 100, 1)}% temporal overlap",
            ),
            ScoreBreakdown(
                component="AIS Gap (Dark Vessel)",
                raw_value=round(s3, 4),
                weight=WEIGHTS["ais_gap"],
                weighted_value=round(WEIGHTS["ais_gap"] * s3, 4),
                explanation="AIS gap detected near origin" if s3 > 0 else "No AIS gap detected during relevant window",
            ),
            ScoreBreakdown(
                component="Course/Speed Anomaly",
                raw_value=round(s4, 4),
                weight=WEIGHTS["course_speed_anomaly"],
                weighted_value=round(WEIGHTS["course_speed_anomaly"] * s4, 4),
                explanation=f"Speed/course deviation score: {round(s4 * 100, 1)}%",
            ),
            ScoreBreakdown(
                component="Vessel Type Prior",
                raw_value=round(s5, 4),
                weight=WEIGHTS["vessel_type_prior"],
                weighted_value=round(WEIGHTS["vessel_type_prior"] * s5, 4),
                explanation=f"Prior probability for vessel type '{track.vessel_type or 'unknown'}': {round(s5 * 100, 1)}%",
            ),
        ]

        has_gap = any(
            g.gap_start <= spill_time <= g.gap_end
            or abs((datetime.fromisoformat(g.gap_start) - datetime.fromisoformat(spill_time)).total_seconds()) < 86400
            for g in track.gaps
        ) if track.gaps else False

        suspects.append(VesselSuspect(
            mmsi=track.mmsi,
            vessel_name=track.vessel_name,
            vessel_type=track.vessel_type,
            composite_score=round(composite, 4),
            confidence=conf,
            score_breakdown=breakdown,
            has_ais_gap=has_gap,
            track_summary=f"{len(track.positions)} positions, {len(track.gaps)} AIS gaps detected",
        ))

    # Sort by composite score descending
    suspects.sort(key=lambda s: s.composite_score, reverse=True)
    return suspects
