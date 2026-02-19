import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  saveUIState,
  loadUIState,
  clearUIState,
  createDefaultState,
  type PersistedUIState,
} from "./persistence";

function makeState(
  overrides: Partial<PersistedUIState> = {},
): PersistedUIState {
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
  key: vi.fn((_index: number) => null),
};

describe("persistence", () => {
  beforeEach(() => {
    store.clear();
    vi.stubGlobal("localStorage", mockLocalStorage);
  });

  describe("createDefaultState", () => {
    it("returns version 2 with vertical layout", () => {
      const state = createDefaultState();
      expect(state.version).toBe(2);
      expect(state.layout.mode).toBe("vertical");
      expect(state.chartOptions).toEqual({});
    });
  });

  describe("saveUIState", () => {
    it("saves state to localStorage", () => {
      const state = makeState({
        layout: { mode: "side-by-side" },
      });
      const result = saveUIState(state);
      expect(result).toBe(true);
      expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
        "openroast-ui-state",
        expect.any(String),
      );
      const raw = store.get("openroast-ui-state");
      expect(raw).not.toBeUndefined();
      const parsed = JSON.parse(raw!);
      expect(parsed.layout.mode).toBe("side-by-side");
    });
  });

  describe("loadUIState", () => {
    it("returns null when nothing stored", () => {
      expect(loadUIState()).toBeNull();
    });

    it("returns saved state", () => {
      const state = makeState({
        layout: { mode: "side-by-side" },
        chartOptions: {
          m1: {
            showET: true,
            showBT: true,
            showETRor: true,
            showBTRor: false,
            showControls: {},
            showExtraChannels: {},
            rorSmoothing: 5,
          },
        },
      });
      saveUIState(state);
      const loaded = loadUIState();
      expect(loaded).not.toBeNull();
      expect(loaded!.layout.mode).toBe("side-by-side");
      expect(loaded!.chartOptions.m1.showETRor).toBe(true);
      expect(loaded!.chartOptions.m1.rorSmoothing).toBe(5);
    });

    it("returns null for invalid JSON", () => {
      store.set("openroast-ui-state", "not json");
      expect(loadUIState()).toBeNull();
    });

    it("returns null for wrong version", () => {
      store.set(
        "openroast-ui-state",
        JSON.stringify({
          version: 1,
          layout: { mode: "vertical" },
          chartOptions: {},
        }),
      );
      expect(loadUIState()).toBeNull();
    });

    it("returns null for missing layout", () => {
      store.set("openroast-ui-state", JSON.stringify({ version: 2 }));
      expect(loadUIState()).toBeNull();
    });

    it("returns null for non-object", () => {
      store.set("openroast-ui-state", '"string"');
      expect(loadUIState()).toBeNull();
    });

    it("returns null for layout missing mode", () => {
      store.set(
        "openroast-ui-state",
        JSON.stringify({ version: 2, layout: {} }),
      );
      expect(loadUIState()).toBeNull();
    });
  });

  describe("clearUIState", () => {
    it("removes stored state", () => {
      saveUIState(makeState());
      clearUIState();
      expect(loadUIState()).toBeNull();
    });
  });

  describe("roundtrip", () => {
    it("preserves full state through save/load", () => {
      const state = makeState({
        layout: { mode: "side-by-side" },
        chartOptions: {
          m1: {
            showET: true,
            showBT: true,
            showETRor: false,
            showBTRor: true,
            showControls: { burner: true },
            showExtraChannels: { Inlet: false },
            rorSmoothing: 3,
          },
        },
      });
      saveUIState(state);
      const loaded = loadUIState();
      expect(loaded).toEqual(state);
    });
  });
});
