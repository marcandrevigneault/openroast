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
