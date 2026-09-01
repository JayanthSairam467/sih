"""
AIS Ingestion & Gap Detection Engine.
Ingests AIS position records, builds per-vessel tracks, detects AIS gaps.
"""

from datetime import datetime, timedelta
from typing import Optional
import math

from app.models.schemas import AisPosition, AisGap, VesselTrack


# ── Vessel type priors for scoring ─────────────────────────────────

VESSEL_TYPE_PRIORS = {
    "tanker": 0.95,
    "cargo": 0.80,
    "chemical_tanker": 0.90,
    "oil_tanker": 0.98,
    "bulk_carrier": 0.60,
    "container": 0.50,
    "fishing": 0.20,
    "passenger": 0.10,
    "tug": 0.15,
    "sailing": 0.05,
    "pleasure": 0.05,
    "unknown": 0.40,
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in km between two lat/lon points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class AISIngestionEngine:
    """Processes raw AIS positions into vessel tracks and detects gaps."""

    def __init__(self):
        self.positions: dict[str, list[AisPosition]] = {}  # mmsi -> positions
        self.vessel_info: dict[str, dict] = {}  # mmsi -> {name, type, imo}

    def ingest(self, positions: list[AisPosition]) -> None:
        """Add a batch of AIS positions."""
        for pos in positions:
            if pos.mmsi not in self.positions:
                self.positions[pos.mmsi] = []
                self.vessel_info[pos.mmsi] = {
                    "name": pos.vessel_name,
                    "type": pos.vessel_type or "unknown",
                    "imo": pos.imo,
                }
            self.positions[pos.mmsi].append(pos)
            # Update vessel info if we got better data
            if pos.vessel_name:
                self.vessel_info[pos.mmsi]["name"] = pos.vessel_name
            if pos.vessel_type:
                self.vessel_info[pos.mmsi]["type"] = pos.vessel_type

            # Sort by timestamp
            self.positions[pos.mmsi].sort(key=lambda p: p.timestamp)

    def detect_gaps(
        self,
        mmsi: str,
        expected_interval_minutes: float = 30.0,
        gap_threshold_factor: float = 3.0,
    ) -> list[AisGap]:
        """
        Detect gaps in a vessel's AIS track.
        A gap = interval between consecutive positions > threshold.
        """
        if mmsi not in self.positions:
            return []

        positions = self.positions[mmsi]
        if len(positions) < 2:
            return []

        threshold = timedelta(minutes=expected_interval_minutes * gap_threshold_factor)
        gaps = []

        for i in range(len(positions) - 1):
            t1 = datetime.fromisoformat(positions[i].timestamp)
            t2 = datetime.fromisoformat(positions[i + 1].timestamp)
            delta = t2 - t1

            if delta > threshold:
                gaps.append(AisGap(
                    mmsi=mmsi,
                    vessel_name=self.vessel_info.get(mmsi, {}).get("name"),
                    gap_start=positions[i].timestamp,
                    gap_end=positions[i + 1].timestamp,
                    gap_duration_hours=round(delta.total_seconds() / 3600, 2),
                    last_known_lat=positions[i].lat,
                    last_known_lon=positions[i].lon,
                    resume_lat=positions[i + 1].lat,
                    resume_lon=positions[i + 1].lon,
                ))

        return gaps

    def get_all_gaps(self) -> list[AisGap]:
        """Detect gaps across all vessel tracks."""
        all_gaps = []
        for mmsi in self.positions:
            all_gaps.extend(self.detect_gaps(mmsi))
        return all_gaps

    def build_tracks(self) -> list[VesselTrack]:
        """Build complete vessel tracks with gaps."""
        tracks = []
        for mmsi, positions in self.positions.items():
            gaps = self.detect_gaps(mmsi)
            info = self.vessel_info.get(mmsi, {})
            tracks.append(VesselTrack(
                mmsi=mmsi,
                vessel_name=info.get("name"),
                vessel_type=info.get("type"),
                positions=positions,
                gaps=gaps,
            ))
        return tracks

    def vessels_in_area(
        self,
        lat: float,
        lon: float,
        radius_km: float,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> list[str]:
        """Return MMSIs of vessels that were within radius_km of a point during a time window."""
        result = []
        for mmsi, positions in self.positions.items():
            for pos in positions:
                dist = haversine_km(lat, lon, pos.lat, pos.lon)
                if dist > radius_km:
                    continue
                if start_time and pos.timestamp < start_time:
                    continue
                if end_time and pos.timestamp > end_time:
                    continue
                result.append(mmsi)
                break  # one hit is enough
        return list(set(result))
