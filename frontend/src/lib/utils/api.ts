/**
 * REST API client for OpenRoast backend.
 */

import type { TemperaturePoint } from "$lib/stores/machine";

export interface ProfileSummary {
  id: string;
  name: string;
  machine: string;
  created_at: string;
  bean_name: string;
  data_points: number;
}

export interface SaveProfileRequest {
  profile: {
    name: string;
    machine: string;
    temperatures: TemperaturePoint[];
    events: {
      event_type: string;
      timestamp_ms: number;
      auto_detected: boolean;
    }[];
    controls: Record<string, [number, number][]>;
  };
  name?: string;
  bean_name?: string;
  bean_weight_g?: number;
}

const BASE = "/api";

export async function saveProfile(
  req: SaveProfileRequest,
): Promise<{ id: string }> {
  const resp = await fetch(`${BASE}/profiles`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!resp.ok) throw new Error(`Save failed: ${resp.status}`);
  return resp.json();
}

export async function listProfiles(): Promise<ProfileSummary[]> {
  const resp = await fetch(`${BASE}/profiles`);
  if (!resp.ok) throw new Error(`List failed: ${resp.status}`);
  return resp.json();
}

export interface FullProfile {
  id: string;
  name: string;
  machine: string;
  created_at: string;
  bean_name: string;
  temperatures: TemperaturePoint[];
  events: {
    event_type: string;
    timestamp_ms: number;
    auto_detected: boolean;
  }[];
  controls: Record<string, [number, number][]>;
}

export async function getProfile(id: string): Promise<FullProfile> {
  const resp = await fetch(`${BASE}/profiles/${id}`);
  if (!resp.ok) throw new Error(`Get profile failed: ${resp.status}`);
  return resp.json();
}

export async function deleteProfile(id: string): Promise<void> {
  const resp = await fetch(`${BASE}/profiles/${id}`, { method: "DELETE" });
  if (!resp.ok) throw new Error(`Delete failed: ${resp.status}`);
}

// --- Schedules ---

export interface ScheduleSummary {
  id: string;
  name: string;
  machine_name: string;
  created_at: string;
  step_count: number;
}

export interface SavedScheduleData {
  id: string;
  name: string;
  machine_name: string;
  created_at: string;
  steps: {
    id: string;
    trigger: Record<string, unknown>;
    actions: { channel: string; value: number }[];
    enabled: boolean;
  }[];
  source_profile_name: string | null;
}

export interface SaveScheduleRequest {
  name: string;
  machine_name: string;
  steps: Record<string, unknown>[];
  source_profile_name?: string | null;
}

export async function saveSchedule(
  req: SaveScheduleRequest,
): Promise<{ id: string }> {
  const resp = await fetch(`${BASE}/schedules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!resp.ok) throw new Error(`Save schedule failed: ${resp.status}`);
  return resp.json();
}

export async function listSchedules(): Promise<ScheduleSummary[]> {
  const resp = await fetch(`${BASE}/schedules`);
  if (!resp.ok) throw new Error(`List schedules failed: ${resp.status}`);
  return resp.json();
}

export async function getSchedule(id: string): Promise<SavedScheduleData> {
  const resp = await fetch(`${BASE}/schedules/${id}`);
  if (!resp.ok) throw new Error(`Get schedule failed: ${resp.status}`);
  return resp.json();
}

export async function deleteSchedule(id: string): Promise<void> {
  const resp = await fetch(`${BASE}/schedules/${id}`, { method: "DELETE" });
  if (!resp.ok) throw new Error(`Delete schedule failed: ${resp.status}`);
}
