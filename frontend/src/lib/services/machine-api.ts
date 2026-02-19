/**
 * REST API client for machine and catalog operations.
 */

const BASE = "/api";

// ── Catalog types ────────────────────────────────────────────────────

export interface ManufacturerSummary {
  id: string;
  name: string;
  country: string;
  model_count: number;
}

export interface CatalogModel {
  id: string;
  name: string;
  protocol: string;
  sampling_interval_ms: number;
  connection: Record<string, unknown>;
  et: Record<string, unknown>;
  bt: Record<string, unknown>;
  extra_channels: Record<string, unknown>[];
  controls: CatalogControl[];
}

export interface CatalogControl {
  name: string;
  channel: string;
  command: string;
  min: number;
  max: number;
  step: number;
  unit: string;
}

// ── Machine types ────────────────────────────────────────────────────

export interface SavedMachineSummary {
  id: string;
  name: string;
  protocol: string;
}

export interface SavedMachine {
  id: string;
  name: string;
  protocol: string;
  connection: Record<string, unknown>;
  sampling_interval_ms: number;
  controls: CatalogControl[];
  extra_channels: Record<string, unknown>[];
  [key: string]: unknown;
}

export interface MachineStatus {
  machine_id: string;
  connected: boolean;
  driver_state: string;
  session_state: string;
}

// ── Catalog API ──────────────────────────────────────────────────────

export async function listManufacturers(): Promise<ManufacturerSummary[]> {
  const resp = await fetch(`${BASE}/catalog/manufacturers`);
  if (!resp.ok) throw new Error(`Failed to list manufacturers: ${resp.status}`);
  return resp.json();
}

export async function listModels(
  manufacturerId: string,
): Promise<CatalogModel[]> {
  const resp = await fetch(
    `${BASE}/catalog/manufacturers/${manufacturerId}/models`,
  );
  if (!resp.ok) throw new Error(`Failed to list models: ${resp.status}`);
  return resp.json();
}

// ── Machine CRUD ─────────────────────────────────────────────────────

export async function listMachines(): Promise<SavedMachineSummary[]> {
  const resp = await fetch(`${BASE}/machines`);
  if (!resp.ok) throw new Error(`Failed to list machines: ${resp.status}`);
  return resp.json();
}

export async function getMachine(machineId: string): Promise<SavedMachine> {
  const resp = await fetch(`${BASE}/machines/${machineId}`);
  if (!resp.ok) throw new Error(`Failed to get machine: ${resp.status}`);
  return resp.json();
}

export async function createFromCatalog(
  manufacturerId: string,
  modelId: string,
  name?: string,
): Promise<{ id: string; machine: SavedMachine }> {
  const resp = await fetch(`${BASE}/machines/from-catalog`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      manufacturer_id: manufacturerId,
      model_id: modelId,
      name: name || undefined,
    }),
  });
  if (!resp.ok) throw new Error(`Failed to create machine: ${resp.status}`);
  return resp.json();
}

export async function deleteMachine(machineId: string): Promise<void> {
  const resp = await fetch(`${BASE}/machines/${machineId}`, {
    method: "DELETE",
  });
  if (!resp.ok) throw new Error(`Failed to delete machine: ${resp.status}`);
}

// ── Machine Connection ───────────────────────────────────────────────

export async function connectMachine(
  machineId: string,
): Promise<{ status: string; machine_id: string }> {
  const resp = await fetch(`${BASE}/machines/${machineId}/connect`, {
    method: "POST",
  });
  if (!resp.ok) {
    const body = await resp
      .json()
      .catch(() => ({ detail: "Connection failed" }));
    throw new Error(body.detail || `Connect failed: ${resp.status}`);
  }
  return resp.json();
}

export async function disconnectMachine(
  machineId: string,
): Promise<{ status: string; machine_id: string }> {
  const resp = await fetch(`${BASE}/machines/${machineId}/disconnect`, {
    method: "POST",
  });
  if (!resp.ok) throw new Error(`Disconnect failed: ${resp.status}`);
  return resp.json();
}

export async function getMachineStatus(
  machineId: string,
): Promise<MachineStatus> {
  const resp = await fetch(`${BASE}/machines/${machineId}/status`);
  if (!resp.ok) throw new Error(`Failed to get status: ${resp.status}`);
  return resp.json();
}
