import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
	saveUIState,
	loadUIState,
	clearUIState,
	createDefaultState,
	DEFAULT_CHART_OPTIONS,
	type PersistedUIState
} from './persistence';

function makeState(overrides: Partial<PersistedUIState> = {}): PersistedUIState {
	return { ...createDefaultState(), ...overrides };
}

// Mock localStorage since jsdom/Node may not provide a full implementation
const store = new Map<string, string>();
const mockLocalStorage = {
	getItem: vi.fn((key: string) => store.get(key) ?? null),
	setItem: vi.fn((key: string, value: string) => store.set(key, value)),
	removeItem: vi.fn((key: string) => store.delete(key)),
	clear: vi.fn(() => store.clear()),
	get length() {
		return store.size;
	},
	key: vi.fn((_index: number) => null)
};

describe('persistence', () => {
	beforeEach(() => {
		store.clear();
		vi.stubGlobal('localStorage', mockLocalStorage);
	});

	describe('createDefaultState', () => {
		it('returns version 1 with empty machines', () => {
			const state = createDefaultState();
			expect(state.version).toBe(1);
			expect(state.dashboard.machines).toEqual([]);
			expect(state.dashboard.layout.mode).toBe('grid');
			expect(state.dashboard.layout.columns).toBe(2);
			expect(state.chartOptions).toEqual({});
		});
	});

	describe('DEFAULT_CHART_OPTIONS', () => {
		it('has ET and BT enabled by default', () => {
			expect(DEFAULT_CHART_OPTIONS.showET).toBe(true);
			expect(DEFAULT_CHART_OPTIONS.showBT).toBe(true);
		});

		it('has optional curves disabled by default', () => {
			expect(DEFAULT_CHART_OPTIONS.showETRor).toBe(false);
			expect(DEFAULT_CHART_OPTIONS.showBTRor).toBe(false);
			expect(DEFAULT_CHART_OPTIONS.showBurner).toBe(false);
			expect(DEFAULT_CHART_OPTIONS.showAirflow).toBe(false);
			expect(DEFAULT_CHART_OPTIONS.showDrum).toBe(false);
		});
	});

	describe('saveUIState', () => {
		it('saves state to localStorage', () => {
			const state = makeState({
				dashboard: {
					machines: [{ id: 'm1', name: 'Roaster 1' }],
					layout: { mode: 'vertical', columns: 1 }
				}
			});
			const result = saveUIState(state);
			expect(result).toBe(true);
			expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
				'openroast-ui-state',
				expect.any(String)
			);
			const raw = store.get('openroast-ui-state');
			expect(raw).not.toBeUndefined();
			const parsed = JSON.parse(raw!);
			expect(parsed.dashboard.machines).toHaveLength(1);
		});
	});

	describe('loadUIState', () => {
		it('returns null when nothing stored', () => {
			expect(loadUIState()).toBeNull();
		});

		it('returns saved state', () => {
			const state = makeState({
				dashboard: {
					machines: [{ id: 'm1', name: 'Roaster 1' }],
					layout: { mode: 'horizontal', columns: 3 }
				},
				chartOptions: {
					m1: { ...DEFAULT_CHART_OPTIONS, showETRor: true }
				}
			});
			saveUIState(state);
			const loaded = loadUIState();
			expect(loaded).not.toBeNull();
			expect(loaded!.dashboard.machines[0].name).toBe('Roaster 1');
			expect(loaded!.dashboard.layout.mode).toBe('horizontal');
			expect(loaded!.chartOptions.m1.showETRor).toBe(true);
		});

		it('returns null for invalid JSON', () => {
			store.set('openroast-ui-state', 'not json');
			expect(loadUIState()).toBeNull();
		});

		it('returns null for wrong version', () => {
			store.set(
				'openroast-ui-state',
				JSON.stringify({ version: 999, dashboard: { machines: [], layout: {} }, chartOptions: {} })
			);
			expect(loadUIState()).toBeNull();
		});

		it('returns null for missing dashboard', () => {
			store.set('openroast-ui-state', JSON.stringify({ version: 1 }));
			expect(loadUIState()).toBeNull();
		});

		it('returns null for non-object', () => {
			store.set('openroast-ui-state', '"string"');
			expect(loadUIState()).toBeNull();
		});
	});

	describe('clearUIState', () => {
		it('removes stored state', () => {
			saveUIState(makeState());
			clearUIState();
			expect(loadUIState()).toBeNull();
		});
	});

	describe('roundtrip', () => {
		it('preserves full state through save/load', () => {
			const state = makeState({
				dashboard: {
					machines: [
						{ id: 'm1', name: 'Stratto Pro 300' },
						{ id: 'm2', name: 'Probat 12' }
					],
					layout: { mode: 'grid', columns: 3 }
				},
				chartOptions: {
					m1: { ...DEFAULT_CHART_OPTIONS, showBurner: true, showAirflow: true },
					m2: { ...DEFAULT_CHART_OPTIONS }
				}
			});
			saveUIState(state);
			const loaded = loadUIState();
			expect(loaded).toEqual(state);
		});
	});
});
