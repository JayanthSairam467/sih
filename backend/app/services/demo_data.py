"""
Demo data service with real-world incidents for demo mode.
Incidents: 2019 Sabiti/Tanker near Jeddah, 2021 X-Press Pearl off Sri Lanka.
"""

import uuid
from datetime import datetime, timedelta

from app.models.schemas import (
    IncidentInfo, IncidentResponse, DetectionResult, ConfidenceLevel,
    AisPosition, VesselTrack, AisGap, AttributionResult, VesselSuspect, ScoreBreakdown,
    DriftResult, DriftPoint,
)
from app.engines.ais_engine import AISIngestionEngine, VESSEL_TYPE_PRIORS
from app.engines.drift import DriftEngine
from app.engines.attribution import compute_attribution, WEIGHTS


# ── Incident definitions ───────────────────────────────────────────

INCIDENTS: dict[str, IncidentInfo] = {
    "sabiti-2019": IncidentInfo(
        id="sabiti-2019",
        name="Sabiti Tanker Incident — Jeddah",
        date="2019-10-11",
        description=(
            "On October 11, 2019, the Iranian oil tanker ABT Simorgh (later renamed Sabiti) "
            "was reportedly damaged near Jeddah, Saudi Arabia. SAR satellite imagery captured "
            "a long oil trail the following day. AIS data showed unusual vessel behavior "
            "in the area — including potential AIS gaps — making this a strong candidate "
            "for dark-vessel detection analysis."
        ),
        location="Red Sea, near Jeddah, Saudi Arabia",
        lat=21.5,
        lon=39.1,
    ),
    "xpress-pearl-2021": IncidentInfo(
        id="xpress-pearl-2021",
        name="X-Press Pearl Disaster — Colombo",
        date="2021-05-20",
        description=(
            "The X-Press Pearl container ship caught fire and sank off Colombo, Sri Lanka "
            "in May 2021, releasing oil and chemical cargo into the Indian Ocean. This is "
            "one of the worst maritime environmental disasters in the Indian Ocean region. "
            "Multiple Sentinel-1 passes captured the pollution plume over several days."
        ),
        location="Indian Ocean, off Colombo, Sri Lanka",
        lat=7.1,
        lon=79.8,
    ),
}


# ── Synthetic but realistic AIS data for each incident ─────────────

def _generate_sabiti_ais() -> list[AisPosition]:
    """
    Synthetic AIS reconstruction for the Sabiti incident area.
    The tanker approaches from the north, goes AIS-dark for ~5 hours during
    the suspected discharge window, then reappears south of the spill area.
    Detection time: 2019-10-12T06:00:00 (oil trail captured by SAR).
    AIS data spans: Oct 11 18:00 → Oct 12 12:00.
    Gap window: 00:00–04:00 on Oct 12 (right around the spill time).
    """
    base_time = datetime(2019, 10, 11, 18, 0)  # Start 12h before detection
    positions = []

    # ── Suspect tanker (MMSI 422000100) — goes dark during spill ──
    # Build hourly positions with explicit timestamps
    tanker_data = [
        # (hour_offset, lat, lon, speed, course) — before gap
        (0, 21.80, 39.25, 12.0, 190),
        (1, 21.75, 39.22, 12.0, 190),
        (2, 21.70, 39.20, 12.0, 190),
        (3, 21.65, 39.18, 12.0, 190),
        (4, 21.60, 39.15, 12.0, 190),
        (5, 21.55, 39.12, 10.0, 190),
        # hours 6-10: GAP (00:00–04:00 Oct 12) — vessel goes dark
        (11, 21.40, 39.05, 8.0, 200),
        (12, 21.35, 39.00, 8.0, 200),
        (13, 21.30, 38.95, 8.0, 200),
        (14, 21.25, 38.90, 8.0, 200),
    ]

    for hour_offset, lat, lon, speed, course in tanker_data:
        t = base_time + timedelta(hours=hour_offset)
        positions.append(AisPosition(
            mmsi="422000100",
            lat=lat,
            lon=lon,
            timestamp=t.isoformat(),
            speed_knots=speed,
            course_deg=float(course),
            vessel_name="ABT SABITI",
            vessel_type="oil_tanker",
            imo="8515200",
        ))

    # ── Cargo vessel nearby (MMSI 538001234) — normal passage, not suspicious ──
    for i in range(24):
        t = base_time + timedelta(hours=i * 0.5)
        positions.append(AisPosition(
            mmsi="538001234",
            lat=21.90 + i * 0.003,
            lon=39.40 - i * 0.005,
            timestamp=t.isoformat(),
            speed_knots=14.0,
            course_deg=210.0,
            vessel_name="PACIFIC VOYAGER",
            vessel_type="cargo",
        ))

    # ── Fishing vessel (MMSI 511000789) — stationary, low suspicion ──
    for i in range(24):
        t = base_time + timedelta(hours=i * 0.5)
        positions.append(AisPosition(
            mmsi="511000789",
            lat=21.40 + 0.002 * (i % 3),
            lon=38.90 + 0.001 * (i % 4),
            timestamp=t.isoformat(),
            speed_knots=3.0,
            course_deg=45.0,
            vessel_name="RED SEA FISHER",
            vessel_type="fishing",
        ))

    # ── Passenger ferry (MMSI 622000456) — far from spill, irrelevant ──
    for i in range(24):
        t = base_time + timedelta(hours=i * 0.5)
        positions.append(AisPosition(
            mmsi="622000456",
            lat=22.00 + i * 0.005,
            lon=39.50 + i * 0.003,
            timestamp=t.isoformat(),
            speed_knots=18.0,
            course_deg=150.0,
            vessel_name="JEDDAH FERRY",
            vessel_type="passenger",
        ))

    return positions


def _generate_xpress_pearl_ais() -> list[AisPosition]:
    """
    Synthetic AIS reconstruction for X-Press Pearl incident.
    The vessel was anchored off Colombo when the fire broke out.
    """
    base_time = datetime(2021, 5, 20, 0, 0)
    positions = []

    # ── X-Press Pearl (MMSI 563005600) — anchored, then distress ──
    for i in range(24):
        t = base_time + timedelta(hours=i)
        # Vessel drifts slightly while anchored, then stays put during fire
        drift = 0.001 * (i if i < 12 else 12)  # minor drift then stops
        positions.append(AisPosition(
            mmsi="563005600",
            lat=7.10 - drift * 0.3,
            lon=79.80 + drift * 0.1,
            timestamp=t.isoformat(),
            speed_knots=0.1 if i < 12 else 0.0,
            course_deg=0.0,
            vessel_name="X-PRESS PEARL",
            vessel_type="container",
            imo="9475749",
        ))

    # ── Tug vessel assisting (MMSI 563005700) ──
    for i in range(24):
        t = base_time + timedelta(hours=i)
        positions.append(AisPosition(
            mmsi="563005700",
            lat=7.09 + 0.005 + 0.001 * (i % 6),
            lon=79.79 + 0.003 * (i % 8),
            timestamp=t.isoformat(),
            speed_knots=2.0,
            course_deg=180.0 if i < 12 else 0.0,
            vessel_name="COLOMBO TUG-1",
            vessel_type="tug",
        ))

    # ── Patrol vessel (MMSI 563005800) — Coast Guard / Navy ──
    for i in range(24):
        t = base_time + timedelta(hours=i)
        positions.append(AisPosition(
            mmsi="563005800",
            lat=7.08 + 0.01 * (i % 10) * 0.1,
            lon=79.82 - 0.005 * (i % 6),
            timestamp=t.isoformat(),
            speed_knots=5.0,
            course_deg=270.0,
            vessel_name="SLCG PATROL-3",
            vessel_type="passenger",
        ))

    return positions


# ── Pre-built incident responses ───────────────────────────────────

def build_sabiti_incident() -> IncidentResponse:
    """Build the complete Sabiti incident response with all data pre-computed."""
    incident = INCIDENTS["sabiti-2019"]

    # Detection
    detection = DetectionResult(
        spill_id="SPILL-SABITI-2019",
        centroid_lat=21.52,
        centroid_lon=39.11,
        area_km2=12.4,
        confidence=ConfidenceLevel.CRITICAL,
        classes_found={"sea_surface": 48500, "oil_spill": 8200, "look_alike": 1800, "ship": 45, "land": 0},
        bbox=[39.02, 21.45, 39.20, 21.60],
    )

    # AIS
    engine = AISIngestionEngine()
    engine.ingest(_generate_sabiti_ais())
    tracks = engine.build_tracks()

    # Drift
    drift_engine = DriftEngine(
        current_speed_kn=0.25,
        current_direction_deg=195,
        wind_speed_ms=4.5,
        wind_direction_deg=310,
    )
    drift_back = drift_engine.trace_backward(
        spill_lat=21.52, spill_lon=39.11,
        detection_time="2019-10-12T06:00:00",
        max_hours=24.0,
    )
    drift_fwd = drift_engine.trace_forward(
        spill_lat=21.52, spill_lon=39.11,
        detection_time="2019-10-12T06:00:00",
        max_hours=48.0,
    )

    # Attribution
    suspects = compute_attribution(
        tracks=tracks,
        origin_lat=drift_back.origin_lat,
        origin_lon=drift_back.origin_lon,
        spill_time="2019-10-12T06:00:00",
        origin_time=drift_back.origin_time,
    )

    return IncidentResponse(
        incident=incident,
        detection=detection,
        vessel_tracks=tracks,
        attribution=AttributionResult(
            spill_id="SPILL-SABITI-2019",
            candidates=suspects,
            top_suspect=suspects[0] if suspects else None,
            origin_estimate=drift_back,
        ),
        drift_forward=drift_fwd,
        drift_backward=drift_back,
    )


def build_xpress_incident() -> IncidentResponse:
    """Build the X-Press Pearl incident response."""
    incident = INCIDENTS["xpress-pearl-2021"]

    detection = DetectionResult(
        spill_id="SPILL-XPRESS-2021",
        centroid_lat=7.095,
        centroid_lon=79.805,
        area_km2=8.7,
        confidence=ConfidenceLevel.HIGH,
        classes_found={"sea_surface": 51000, "oil_spill": 5400, "look_alike": 3200, "ship": 60, "land": 0},
        bbox=[79.78, 7.08, 79.83, 7.11],
    )

    engine = AISIngestionEngine()
    engine.ingest(_generate_xpress_pearl_ais())
    tracks = engine.build_tracks()

    drift_engine = DriftEngine(
        current_speed_kn=0.2,
        current_direction_deg=240,
        wind_speed_ms=6.0,
        wind_direction_deg=180,
    )
    drift_back = drift_engine.trace_backward(
        spill_lat=7.095, spill_lon=79.805,
        detection_time="2021-05-21T08:00:00",
        max_hours=24.0,
    )
    drift_fwd = drift_engine.trace_forward(
        spill_lat=7.095, spill_lon=79.805,
        detection_time="2021-05-21T08:00:00",
        max_hours=48.0,
    )

    suspects = compute_attribution(
        tracks=tracks,
        origin_lat=drift_back.origin_lat,
        origin_lon=drift_back.origin_lon,
        spill_time="2021-05-21T08:00:00",
        origin_time=drift_back.origin_time,
    )

    return IncidentResponse(
        incident=incident,
        detection=detection,
        vessel_tracks=tracks,
        attribution=AttributionResult(
            spill_id="SPILL-XPRESS-2021",
            candidates=suspects,
            top_suspect=suspects[0] if suspects else None,
            origin_estimate=drift_back,
        ),
        drift_forward=drift_fwd,
        drift_backward=drift_back,
    )


# ── Registry ───────────────────────────────────────────────────────

INCIDENT_BUILDERS = {
    "sabiti-2019": build_sabiti_incident,
    "xpress-pearl-2021": build_xpress_incident,
}
