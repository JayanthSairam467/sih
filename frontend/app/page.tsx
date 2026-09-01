"use client";

import { useState, useEffect } from "react";
import Header from "@/components/Header";
import MapView from "@/components/MapView";
import SuspectPanel from "@/components/SuspectPanel";
import IncidentInfoPanel from "@/components/IncidentInfoPanel";
import {
  listIncidents,
  getIncident,
  IncidentInfo,
  IncidentResponse,
} from "@/lib/api";

export default function Dashboard() {
  const [incidents, setIncidents] = useState<IncidentInfo[]>([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(
    null
  );
  const [incidentData, setIncidentData] = useState<IncidentResponse | null>(
    null
  );
  const [selectedMmsi, setSelectedMmsi] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [leftOpen, setLeftOpen] = useState(true);
  const [rightOpen, setRightOpen] = useState(true);

  // Load incidents on mount
  useEffect(() => {
    listIncidents()
      .then((res) => setIncidents(res.incidents))
      .catch((err) => setError("Failed to connect to backend: " + err.message));
  }, []);

  // Load incident data when selected
  useEffect(() => {
    if (!selectedIncidentId) {
      setIncidentData(null);
      setSelectedMmsi(null);
      return;
    }

    setLoading(true);
    setError(null);
    getIncident(selectedIncidentId)
      .then((data) => {
        setIncidentData(data);
        setSelectedMmsi(null);
      })
      .catch((err) => setError("Failed to load incident: " + err.message))
      .finally(() => setLoading(false));
  }, [selectedIncidentId]);

  return (
    <div className="flex flex-col h-screen">
      <Header
        incidents={incidents}
        selectedId={selectedIncidentId}
        onSelect={setSelectedIncidentId}
        loading={loading}
      />

      {error && (
        <div className="px-4 py-2 bg-red-900/50 border-b border-red-700 text-red-300 text-sm flex items-center justify-between">
          <span>⚠ {error}</span>
          <button
            onClick={() => setError(null)}
            className="text-red-400 hover:text-red-200"
          >
            ✕
          </button>
        </div>
      )}

      {/* Main content: Map-first layout */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Left panel - collapsible */}
        <div
          className={`absolute top-0 left-0 z-20 h-full bg-card border-r border-card-border overflow-y-auto transition-all duration-300 ${
            leftOpen ? "w-72" : "w-0 border-r-0"
          }`}
        >
          {leftOpen && <IncidentInfoPanel data={incidentData} />}
        </div>

        {/* Map - always takes full width */}
        <div className="flex-1 relative">
          <MapView
            detection={incidentData?.detection || null}
            vesselTracks={incidentData?.vessel_tracks || []}
            driftForward={incidentData?.drift_forward || null}
            driftBackward={incidentData?.drift_backward || null}
            selectedMmsi={selectedMmsi}
          />

          {/* Toggle buttons */}
          <button
            onClick={() => setLeftOpen(!leftOpen)}
            className="absolute top-2 left-2 z-30 bg-gray-900/90 border border-gray-600 rounded px-2 py-1 text-xs text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
            title={leftOpen ? "Hide incident details" : "Show incident details"}
          >
            {leftOpen ? "◀ Info" : "▶ Info"}
          </button>

          <button
            onClick={() => setRightOpen(!rightOpen)}
            className="absolute top-2 right-2 z-30 bg-gray-900/90 border border-gray-600 rounded px-2 py-1 text-xs text-gray-300 hover:bg-gray-800 hover:text-white transition-colors"
            title={rightOpen ? "Hide suspects" : "Show suspects"}
          >
            {rightOpen ? "Suspects ▶" : "◀ Suspects"}
          </button>
        </div>

        {/* Right panel - collapsible */}
        <div
          className={`absolute top-0 right-0 z-20 h-full bg-card border-l border-card-border overflow-y-auto transition-all duration-300 ${
            rightOpen ? "w-80" : "w-0 border-l-0"
          }`}
        >
          {rightOpen && (
            <SuspectPanel
              suspects={incidentData?.attribution?.candidates || []}
              selectedMmsi={selectedMmsi}
              onSelect={setSelectedMmsi}
            />
          )}
        </div>
      </div>

      <footer className="flex items-center justify-between px-4 py-1.5 bg-card border-t border-card-border text-xs text-gray-500">
        <div className="flex items-center gap-4">
          <span>🛰️ Sagar Rakshak v0.1 · SIH26143 · NTRO</span>
          {incidentData && (
            <span className="text-gray-600">
              {incidentData.vessel_tracks.length} vessels ·{" "}
              {incidentData.attribution.candidates.length} candidates · Drift
              model: Simplified Lagrangian advection
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-gray-600">IFC-IOR / IMAC compatible</span>
          <div className="w-1.5 h-1.5 rounded-full bg-accent-green" />
        </div>
      </footer>
    </div>
  );
}
