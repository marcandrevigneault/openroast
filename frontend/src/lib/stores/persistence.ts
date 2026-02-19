/**
 * Persist and restore UI state via localStorage.
 *
 * Stores dashboard layout, machine list, and per-machine chart options.
 * Temperature history, session state, and slider positions are NOT persisted
 * (they are live/ephemeral data).
 */

const STORAGE_KEY = 'openroast-ui-state';
const CURRENT_VERSION = 1;

export type LayoutMode = 'grid' | 'horizontal' | 'vertical';

export interface PersistedLayout {
	mode: LayoutMode;
	columns: number;
}

export interface PersistedMachine {
	id: string;
	name: string;
}

export interface PersistedChartOptions {
	showET: boolean;
	showBT: boolean;
	showETRor: boolean;
	showBTRor: boolean;
	showBurner: boolean;
	showAirflow: boolean;
	showDrum: boolean;
}

export interface PersistedUIState {
	version: number;
	dashboard: {
		machines: PersistedMachine[];
		layout: PersistedLayout;
	};
	chartOptions: Record<string, PersistedChartOptions>;
}

export const DEFAULT_CHART_OPTIONS: PersistedChartOptions = {
	showET: true,
	showBT: true,
	showETRor: false,
	showBTRor: false,
	showBurner: false,
	showAirflow: false,
	showDrum: false
};

export function createDefaultState(): PersistedUIState {
	return {
		version: CURRENT_VERSION,
		dashboard: {
			machines: [],
			layout: { mode: 'grid', columns: 2 }
		},
		chartOptions: {}
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
		if (typeof parsed !== 'object' || parsed === null) return null;
		if (parsed.version !== CURRENT_VERSION) return null;
		if (!parsed.dashboard || !Array.isArray(parsed.dashboard.machines)) return null;
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
