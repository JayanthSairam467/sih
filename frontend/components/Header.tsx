"use client";

import { IncidentInfo } from "@/lib/api";

interface HeaderProps {
  incidents: IncidentInfo[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  loading: boolean;
}

export default function Header({
  incidents,
  selectedId,
  onSelect,
  loading,
}: HeaderProps) {
  return (
    <header className="flex items-center justify-between px-4 py-3 bg-card border-b border-card-border">
      {/* Logo + Title */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-accent-blue flex items-center justify-center text-sm font-bold">
          🌊
        </div>
        <div>
          <h1 className="text-lg font-bold tracking-wide">
            SAGAR RAKSHAK
          </h1>
          <p className="text-xs text-gray-400">
            Satellite-AIS Maritime Pollution Attribution — SIH26143
          </p>
        </div>
      </div>

      {/* Incident Selector */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-400 uppercase tracking-wider">
            Incident:
          </label>
          <select
            value={selectedId || ""}
            onChange={(e) => onSelect(e.target.value)}
            disabled={loading}
            className="bg-gray-800 border border-gray-600 rounded px-3 py-1.5 text-sm
                       focus:outline-none focus:border-accent-blue disabled:opacity-50"
          >
            <option value="">Select incident...</option>
            {incidents.map((inc) => (
              <option key={inc.id} value={inc.id}>
                {inc.name} ({inc.date})
              </option>
            ))}
          </select>
          {loading && (
            <span className="text-accent-cyan text-xs animate-pulse">
              Loading...
            </span>
          )}
        </div>

        {/* Demo Mode Badge */}
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-gray-800 border border-gray-600">
          <div className="w-2 h-2 rounded-full bg-accent-green animate-pulse" />
          <span className="text-xs text-gray-300">DEMO MODE</span>
        </div>
      </div>
    </header>
  );
}
