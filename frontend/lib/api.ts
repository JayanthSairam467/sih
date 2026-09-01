/**
 * Sagar Rakshak API client.
 * All backend communication goes through this module.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Types ─────────────────────────────────────────────────────────

export type ConfidenceLevel = "Low" | "Medium" | "High" | "Critical";

export interface IncidentInfo {
  id: string;
  name: string;
  date: string;
  description: string;
  location: string;
  lat: number;
  lon: number;
}

export interface DetectionResult {
  spill_id: string;
  centroid_lat: number;
  centroid_lon: number;
  area_km2: number;
  confidence: ConfidenceLevel;
  classes_found: Record<string, number>;
  bbox: number[];
}

export interface AisPosition {
  mmsi: string;
  lat: number;
  lon: number;
  timestamp: string;
  speed_knots: number;
  course_deg: number;
  vessel_name?: string;
  vessel_type?: string;
}

export interface AisGap {
  mmsi: string;
  vessel_name?: string;
  gap_start: string;
  gap_end: string;
  gap_duration_hours: number;
  last_known_lat: number;
  last_known_lon: number;
  resume_lat: number;
  resume_lon: number;
}

export interface VesselTrack {
  mmsi: string;
  vessel_name?: string;
  vessel_type?: string;
  positions: AisPosition[];
  gaps: AisGap[];
}

export interface ScoreBreakdown {
  component: string;
  raw_value: number;
  weight: number;
  weighted_value: number;
  explanation: string;
}

export interface VesselSuspect {
  mmsi: string;
  vessel_name?: string;
  vessel_type?: string;
  composite_score: number;
  confidence: ConfidenceLevel;
  score_breakdown: ScoreBreakdown[];
  has_ais_gap: boolean;
  track_summary?: string;
}

export interface DriftPoint {
  lat: number;
  lon: number;
  timestamp: string;
  step_hours: number;
}

export interface DriftResult {
  origin_lat: number;
  origin_lon: number;
  origin_time: string;
  trajectory: DriftPoint[];
  model_label: string;
}

export interface AttributionResult {
  spill_id: string;
  candidates: VesselSuspect[];
  top_suspect: VesselSuspect | null;
  origin_estimate: DriftResult;
}

export interface IncidentResponse {
  incident: IncidentInfo;
  detection: DetectionResult;
  vessel_tracks: VesselTrack[];
  attribution: AttributionResult;
  drift_forward: DriftResult;
  drift_backward: DriftResult;
}

// ── API calls ─────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

export async function listIncidents(): Promise<{ incidents: IncidentInfo[] }> {
  return apiFetch("/api/demo/incidents");
}

export async function getIncident(id: string): Promise<IncidentResponse> {
  return apiFetch(`/api/demo/incidents/${id}`);
}

export async function detectSpill(data: {
  lat: number;
  lon: number;
  timestamp: string;
}): Promise<DetectionResult> {
  return apiFetch("/api/detection/detect", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getDriftBackward(data: {
  lat: number;
  lon: number;
  detection_time: string;
  max_hours?: number;
}): Promise<DriftResult> {
  return apiFetch("/api/drift/backward", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getDriftForward(data: {
  lat: number;
  lon: number;
  detection_time: string;
  max_hours?: number;
}): Promise<DriftResult> {
  return apiFetch("/api/drift/forward", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getAttributionWeights(): Promise<Record<string, number>> {
  return apiFetch("/api/attribution/weights");
}
