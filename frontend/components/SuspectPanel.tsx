"use client";

import { VesselSuspect, ConfidenceLevel } from "@/lib/api";

interface SuspectPanelProps {
  suspects: VesselSuspect[];
  selectedMmsi: string | null;
  onSelect: (mmsi: string | null) => void;
}

function confidenceBadge(level: ConfidenceLevel) {
  const cls =
    level === "Critical"
      ? "badge-critical glow-critical"
      : level === "High"
        ? "badge-high"
        : level === "Medium"
          ? "badge-medium"
          : "badge-low";

  return (
    <span
      className={`px-2 py-0.5 rounded text-xs font-semibold ${cls}`}
    >
      {level}
    </span>
  );
}

function scoreBar(value: number, max: number = 1) {
  const pct = Math.min(100, (value / max) * 100);
  let color = "bg-gray-500";
  if (value >= 0.75) color = "bg-red-500";
  else if (value >= 0.5) color = "bg-orange-500";
  else if (value >= 0.25) color = "bg-yellow-500";
  else color = "bg-blue-500";

  return (
    <div className="w-full h-1.5 bg-gray-700 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full score-bar ${color}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

export default function SuspectPanel({
  suspects,
  selectedMmsi,
  onSelect,
}: SuspectPanelProps) {
  if (suspects.length === 0) {
    return (
      <div className="p-4 text-gray-500 text-sm">
        No candidates identified. Load an incident to begin analysis.
      </div>
    );
  }

  return (
    <div className="overflow-y-auto max-h-full">
      <div className="p-3 border-b border-card-border">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400">
          Suspect Ranking
        </h2>
        <p className="text-xs text-gray-500 mt-1">
          {suspects.length} vessels analyzed · Top suspect highlighted
        </p>
      </div>

      <div className="space-y-1 p-2">
        {suspects.map((suspect, idx) => {
          const isSelected = suspect.mmsi === selectedMmsi;
          const isTop = idx === 0 && suspect.composite_score > 0.3;

          return (
            <div
              key={suspect.mmsi}
              onClick={() =>
                onSelect(isSelected ? null : suspect.mmsi)
              }
              className={`
                p-3 rounded-lg cursor-pointer transition-all border
                ${
                  isSelected
                    ? "bg-gray-800 border-accent-blue"
                    : isTop
                      ? "bg-gray-800/50 border-accent-red/30 hover:border-accent-red/60"
                      : "bg-gray-900/30 border-transparent hover:bg-gray-800/30 hover:border-gray-600"
                }
              `}
            >
              {/* Header row */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs font-mono ${
                      isTop ? "text-accent-red" : "text-gray-500"
                    }`}
                  >
                    #{idx + 1}
                  </span>
                  <span className="text-sm font-semibold">
                    {suspect.vessel_name || suspect.mmsi}
                  </span>
                  {suspect.has_ais_gap && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-red-900/50 text-red-300 border border-red-700">
                      ⚠ AIS GAP
                    </span>
                  )}
                </div>
                {confidenceBadge(suspect.confidence)}
              </div>

              {/* Vessel info */}
              <div className="mt-1 flex items-center gap-3 text-xs text-gray-400">
                <span>MMSI: {suspect.mmsi}</span>
                <span className="capitalize">
                  {suspect.vessel_type || "unknown"}
                </span>
                <span>Score: {(suspect.composite_score * 100).toFixed(1)}%</span>
              </div>

              {/* Score bar */}
              <div className="mt-2">
                {scoreBar(suspect.composite_score)}
              </div>

              {/* Expanded breakdown */}
              {isSelected && (
                <div className="mt-3 pt-3 border-t border-gray-700 space-y-2">
                  {suspect.score_breakdown.map((comp) => (
                    <div key={comp.component} className="space-y-0.5">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-300">
                          {comp.component}
                        </span>
                        <span className="text-gray-400 font-mono">
                          {(comp.weighted_value * 100).toFixed(1)}%
                        </span>
                      </div>
                      {scoreBar(comp.weighted_value)}
                      <p className="text-xs text-gray-500">
                        {comp.explanation}
                      </p>
                    </div>
                  ))}
                  {suspect.track_summary && (
                    <div className="text-xs text-gray-500 pt-1 border-t border-gray-800">
                      📊 {suspect.track_summary}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
