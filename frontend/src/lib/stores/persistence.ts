/**
 * Persist and restore UI state via localStorage.
 *
 * Stores dashboard layout and per-machine chart options.
 * Temperature history, session state, and slider positions are NOT persisted
 * (they are live/ephemeral data).
 */

import type { LayoutMode, LayoutConfig } from "./dashboard";
import type { ChartOptions } from "./chart-options";

const STORAGE_KEY = "openroast-ui-state";
const CURRENT_VERSION = 2;

export interface PersistedUIState {
  version: number;
  layout: LayoutConfig;
  chartOptions: Record<string, ChartOptions>;
}

export function createDefaultState(): PersistedUIState {
  return {
    version: CURRENT_VERSION,
    layout: { mode: "vertical" as LayoutMode },
    chartOptions: {},
  };
}

export function saveUIState(state: PersistedUIState): boolean {
  try {
    const json = JSON.stringify(state);
    localStorage.setItem(STORAGE_KEY, json);
    return true;
  } catch {
    return false;
  }
}

export function loadUIState(): PersistedUIState | null {
  try {
    const json = localStorage.getItem(STORAGE_KEY);
    if (!json) return null;
    const parsed = JSON.parse(json);
    if (typeof parsed !== "object" || parsed === null) return null;
    if (parsed.version !== CURRENT_VERSION) return null;
    if (!parsed.layout || typeof parsed.layout.mode !== "string") return null;
    return parsed as PersistedUIState;
  } catch {
    return null;
  }
}

export function clearUIState(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // SSR or quota error — ignore
  }
}
