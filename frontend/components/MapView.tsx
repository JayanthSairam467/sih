"use client";

import { useEffect, useRef } from "react";
import { DetectionResult, VesselTrack, DriftResult } from "@/lib/api";

interface MapViewProps {
  detection: DetectionResult | null;
  vesselTracks: VesselTrack[];
  driftForward: DriftResult | null;
  driftBackward: DriftResult | null;
  selectedMmsi: string | null;
}

const VESSEL_COLORS: Record<string, string> = {
  oil_tanker: "#ef4444", tanker: "#ef4444", chemical_tanker: "#f97316",
  cargo: "#3b82f6", container: "#3b82f6", bulk_carrier: "#6366f1",
  fishing: "#22c55e", passenger: "#a855f7", tug: "#eab308", unknown: "#6b7280",
};

function getColor(type?: string): string {
  return VESSEL_COLORS[type?.toLowerCase() || ""] || "#6b7280";
}

export default function MapView({
  detection, vesselTracks, driftForward, driftBackward, selectedMmsi,
}: MapViewProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const leafletMap = useRef<any>(null);
  const initDone = useRef(false);

  // Initialize Leaflet (dynamic import to avoid SSR issues)
  useEffect(() => {
    if (!mapRef.current || initDone.current) return;
    initDone.current = true;

    (async () => {
      const L = (await import("leaflet")).default;
      await import("leaflet/dist/leaflet.css");

      const m = L.map(mapRef.current!, {
        center: [21.5, 39.1],
        zoom: 6,
        zoomControl: false,
      });

      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap",
        maxZoom: 19,
      }).addTo(m);

      L.control.zoom({ position: "topright" }).addTo(m);
      leafletMap.current = m;
    })();

    return () => {
      leafletMap.current?.remove();
      leafletMap.current = null;
    };
  }, []);

  // Update overlays when data changes
  useEffect(() => {
    const m = leafletMap.current;
    if (!m) return;

    (async () => {
      const L = (await import("leaflet")).default;

      // Remove old overlays
      m.eachLayer((layer: any) => {
        if (layer instanceof L.TileLayer) return; // Keep base tiles
        m.removeLayer(layer);
      });

      if (!detection) return;

      // Spill polygon
      if (detection.bbox?.length === 4) {
        const [minLon, minLat, maxLon, maxLat] = detection.bbox;
        const spillColor =
          detection.confidence === "Critical" ? "#ef4444" :
          detection.confidence === "High" ? "#f97316" :
          detection.confidence === "Medium" ? "#eab308" : "#3b82f6";

        L.polygon(
          [[minLat, minLon], [minLat, maxLon], [maxLat, maxLon], [maxLat, minLon]],
          { color: spillColor, fillColor: spillColor, fillOpacity: 0.35, weight: 3 }
        ).addTo(m);
      }

      // Drift backward (orange dashed)
      if (driftBackward?.trajectory?.length) {
        const coords = driftBackward.trajectory.map((p) => [p.lat, p.lon] as [number, number]);
        L.polyline(coords, { color: "#f97316", weight: 3, dashArray: "8, 6" }).addTo(m);
      }

      // Drift forward (green dashed)
      if (driftForward?.trajectory?.length) {
        const coords = driftForward.trajectory.map((p) => [p.lat, p.lon] as [number, number]);
        L.polyline(coords, { color: "#22c55e", weight: 3, dashArray: "6, 8" }).addTo(m);
      }

      // Origin marker
      if (driftBackward) {
        L.circleMarker([driftBackward.origin_lat, driftBackward.origin_lon], {
          radius: 10, color: "#ffffff", fillColor: "#f97316", fillOpacity: 1, weight: 3,
        }).addTo(m);
        L.marker([driftBackward.origin_lat, driftBackward.origin_lon], {
          icon: L.divIcon({
            className: "",
            html: '<div style="color:#f97316;font-size:11px;font-weight:bold;text-shadow:0 0 4px #000,-1px -1px 0 #000,1px -1px 0 #000,-1px 1px 0 #000,1px 1px 0 #000;white-space:nowrap;">ORIGIN</div>',
            iconAnchor: [20, 5],
          }),
        }).addTo(m);
      }

      // Vessel tracks + points
      const allCoords: [number, number][] = [];
      vesselTracks.forEach((track) => {
        const color = getColor(track.vessel_type);
        const isSel = track.mmsi === selectedMmsi;

        if (track.positions.length >= 2) {
          const coords = track.positions.map((p) => [p.lat, p.lon] as [number, number]);
          L.polyline(coords, { color, weight: isSel ? 4 : 2, opacity: 0.9 }).addTo(m);
          coords.forEach((c) => allCoords.push(c));
        }

        track.positions.forEach((pos) => {
          allCoords.push([pos.lat, pos.lon]);
          L.circleMarker([pos.lat, pos.lon], {
            radius: isSel ? 7 : 4, color: "#ffffff", fillColor: color, fillOpacity: 1, weight: 1.5,
          }).addTo(m);
        });
      });

      // Gap markers
      vesselTracks.forEach((track) => {
        track.gaps.forEach((gap) => {
          L.marker([gap.last_known_lat, gap.last_known_lon], {
            icon: L.divIcon({
              className: "",
              html: '<div style="color:#ef4444;font-size:12px;font-weight:bold;text-shadow:0 0 4px #000,-1px -1px 0 #000,1px -1px 0 #000,-1px 1px 0 #000,1px 1px 0 #000;white-space:nowrap;">⚠ DARK</div>',
              iconAnchor: [0, -20],
            }),
          }).addTo(m);
        });
      });

      // Fit bounds
      if (allCoords.length > 0) {
        const bounds = L.latLngBounds(allCoords);
        if (detection.bbox?.length === 4) {
          bounds.extend([detection.bbox[1], detection.bbox[0]]);
          bounds.extend([detection.bbox[3], detection.bbox[2]]);
        }
        driftBackward?.trajectory?.forEach((p) => bounds.extend([p.lat, p.lon]));
        driftForward?.trajectory?.forEach((p) => bounds.extend([p.lat, p.lon]));
        m.fitBounds(bounds.pad(0.1));
      }

      // Fix sizing
      setTimeout(() => m.invalidateSize(), 50);
    })();
  }, [detection, vesselTracks, driftForward, driftBackward, selectedMmsi]);

  return (
    <div className="relative w-full h-full rounded-lg overflow-hidden border border-card-border">
      <div ref={mapRef} className="w-full h-full" />
      {detection && (
        <div className="absolute bottom-4 left-4 bg-gray-900/90 border border-gray-700 rounded-lg p-3 text-xs space-y-1.5 z-[1000]">
          <div className="font-semibold text-gray-300 mb-2">Legend</div>
          <div className="flex items-center gap-2"><span className="w-3 h-3 rounded bg-red-500 opacity-70" /><span>Spill Overlay</span></div>
          <div className="flex items-center gap-2"><span className="w-3 h-3 rounded bg-orange-500" /><span>Drift Backward → origin</span></div>
          <div className="flex items-center gap-2"><span className="w-3 h-3 rounded bg-green-500" /><span>Drift Forward (+48h)</span></div>
          <div className="flex items-center gap-2"><span className="w-3 h-3 rounded-full bg-orange-400 border-2 border-white" /><span>Origin Estimate</span></div>
          <div className="flex items-center gap-2"><span className="text-red-500 font-bold text-sm">⚠</span><span>AIS Gap (Dark Vessel)</span></div>
          <div className="border-t border-gray-700 pt-1 mt-1 space-y-0.5">
            <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-red-500" /><span className="text-gray-400">Oil Tanker</span></div>
            <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-blue-500" /><span className="text-gray-400">Cargo</span></div>
            <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-green-500" /><span className="text-gray-400">Fishing</span></div>
            <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-purple-500" /><span className="text-gray-400">Passenger</span></div>
          </div>
        </div>
      )}
    </div>
  );
}
