"use client";

import { IncidentResponse } from "@/lib/api";

interface IncidentInfoPanelProps {
  data: IncidentResponse | null;
}

export default function IncidentInfoPanel({ data }: IncidentInfoPanelProps) {
  if (!data) {
    return (
      <div className="p-4 text-gray-500 text-sm">
        Select an incident from the dropdown above to begin analysis.
      </div>
    );
  }

  const { incident, detection, attribution } = data;

  return (
    <div className="p-4 space-y-4 overflow-y-auto max-h-full">
      {/* Incident Header */}
      <div>
        <h3 className="text-base font-bold text-white">{incident.name}</h3>
        <p className="text-xs text-gray-400 mt-0.5">
          {incident.date} · {incident.location}
        </p>
        <p className="text-xs text-gray-300 mt-2 leading-relaxed">
          {incident.description}
        </p>
      </div>

      {/* Detection Summary */}
      <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-800">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
          Detection Result
        </h4>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <span className="text-gray-500">Spill ID</span>
            <p className="font-mono text-accent-cyan">{detection.spill_id}</p>
          </div>
          <div>
            <span className="text-gray-500">Confidence</span>
            <p>
              <span
                className={`font-semibold ${
                  detection.confidence === "Critical"
                    ? "text-red-400"
                    : detection.confidence === "High"
                      ? "text-orange-400"
                      : "text-yellow-400"
                }`}
              >
                {detection.confidence}
              </span>
            </p>
          </div>
          <div>
            <span className="text-gray-500">Area</span>
            <p className="text-white">{detection.area_km2} km²</p>
          </div>
          <div>
            <span className="text-gray-500">Centroid</span>
            <p className="font-mono text-gray-300">
              {detection.centroid_lat.toFixed(4)}°, {detection.centroid_lon.toFixed(4)}°
            </p>
          </div>
        </div>

        {/* Class breakdown */}
        <div className="mt-3 pt-2 border-t border-gray-800">
          <h5 className="text-xs text-gray-500 mb-1">Pixel Classification</h5>
          <div className="flex flex-wrap gap-2">
            {Object.entries(detection.classes_found).map(([cls, count]) => (
              <span
                key={cls}
                className={`text-xs px-2 py-0.5 rounded ${
                  cls === "oil_spill"
                    ? "bg-red-900/40 text-red-300"
                    : cls === "look_alike"
                      ? "bg-yellow-900/40 text-yellow-300"
                      : cls === "ship"
                        ? "bg-blue-900/40 text-blue-300"
                        : "bg-gray-800 text-gray-400"
                }`}
              >
                {cls}: {count.toLocaleString()}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Scoring Weights */}
      <div className="bg-gray-900/50 rounded-lg p-3 border border-gray-800">
        <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
          Attribution Formula
        </h4>
        <div className="text-xs text-gray-300 font-mono space-y-1">
          <div>
            <span className="text-blue-400">30%</span> × Spatial Proximity
          </div>
          <div>
            <span className="text-cyan-400">25%</span> × Temporal Fit
          </div>
          <div>
            <span className="text-red-400">20%</span> × AIS Gap (Dark Vessel)
          </div>
          <div>
            <span className="text-orange-400">15%</span> × Course/Speed Anomaly
          </div>
          <div>
            <span className="text-purple-400">10%</span> × Vessel Type Prior
          </div>
        </div>
      </div>

      {/* Top suspect quick view */}
      {attribution.top_suspect && (
        <div className="bg-gray-900/50 rounded-lg p-3 border border-red-800/50">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-red-400 mb-2">
            🎯 Top Suspect
          </h4>
          <div className="text-sm font-semibold text-white">
            {attribution.top_suspect.vessel_name || attribution.top_suspect.mmsi}
          </div>
          <div className="text-xs text-gray-400 mt-1">
            {attribution.top_suspect.vessel_type} · Score:{" "}
            {(attribution.top_suspect.composite_score * 100).toFixed(1)}% ·{" "}
            <span className="text-red-400 font-semibold">
              {attribution.top_suspect.confidence}
            </span>
          </div>
          {attribution.top_suspect.has_ais_gap && (
            <div className="mt-2 text-xs text-red-300 bg-red-900/30 px-2 py-1 rounded">
              ⚠ Vessel went AIS-DARK during spill window — highest-suspicion
              case
            </div>
          )}
        </div>
      )}
    </div>
  );
}
