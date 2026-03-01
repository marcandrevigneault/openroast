/**
 * REST API client for simulator operations.
 */

const BASE = "/api";

// ── Types ───────────────────────────────────────────────────────────

export interface SimulatorInfo {
  machine_id: string;
  catalog_id: string;
  manufacturer_id: string;
  name: string;
  port: number;
  host: string;
}

export interface StartSimulatorRequest {
  manufacturer_id: string;
  model_id: string;
  port?: number;
  name?: string;
}

// ── Simulator API ───────────────────────────────────────────────────

export async function listSimulators(): Promise<SimulatorInfo[]> {
  const resp = await fetch(`${BASE}/simulator`);
  if (!resp.ok) throw new Error(`Failed to list simulators: ${resp.status}`);
  return resp.json();
}

export async function startSimulator(
  req: StartSimulatorRequest,
): Promise<SimulatorInfo> {
  const resp = await fetch(`${BASE}/simulator/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (resp.status === 404) {
    throw new Error("Catalog model not found");
  }
  if (!resp.ok) throw new Error(`Failed to start simulator: ${resp.status}`);
  return resp.json();
}

export async function stopSimulator(machineId: string): Promise<void> {
  const resp = await fetch(`${BASE}/simulator/${machineId}/stop`, {
    method: "POST",
  });
  if (resp.status === 404) {
    throw new Error("Simulator not found or already stopped");
  }
  if (!resp.ok) throw new Error(`Failed to stop simulator: ${resp.status}`);
}
