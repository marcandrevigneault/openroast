/**
 * Dashboard state management — tracks which machines are displayed
 * and how they are laid out.
 */

export type LayoutMode = "grid" | "horizontal" | "vertical";

export interface LayoutConfig {
  mode: LayoutMode;
  columns: number; // 1–4, relevant in grid mode
}

export interface DashboardMachine {
  id: string;
  name: string;
}

export interface DashboardState {
  machines: DashboardMachine[];
  layout: LayoutConfig;
}

export const DEFAULT_LAYOUT: LayoutConfig = {
  mode: "grid",
  columns: 2,
};

export function createDashboardState(): DashboardState {
  return {
    machines: [],
    layout: { ...DEFAULT_LAYOUT },
  };
}

export function addMachine(
  state: DashboardState,
  machine: DashboardMachine,
): DashboardState {
  if (state.machines.some((m) => m.id === machine.id)) return state;
  return { ...state, machines: [...state.machines, machine] };
}

export function removeMachine(
  state: DashboardState,
  machineId: string,
): DashboardState {
  return {
    ...state,
    machines: state.machines.filter((m) => m.id !== machineId),
  };
}

export function updateLayout(
  state: DashboardState,
  layout: Partial<LayoutConfig>,
): DashboardState {
  return { ...state, layout: { ...state.layout, ...layout } };
}

let nextId = 1;
export function generateMachineId(): string {
  return `machine-${nextId++}`;
}
