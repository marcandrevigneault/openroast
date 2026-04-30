import { describe, it, expect, beforeEach, vi } from "vitest";
import { theme } from "./theme.svelte";

const store = new Map<string, string>();
const mockLocalStorage = {
  getItem: vi.fn((key: string) => store.get(key) ?? null),
  setItem: vi.fn((key: string, value: string) => store.set(key, value)),
  removeItem: vi.fn((key: string) => store.delete(key)),
  clear: vi.fn(() => store.clear()),
  get length() {
    return store.size;
  },
  key: vi.fn(() => null),
};

vi.stubGlobal("localStorage", mockLocalStorage);

describe("theme store", () => {
  beforeEach(() => {
    store.clear();
    document.documentElement.removeAttribute("data-theme");
    theme.set("dark");
  });

  it("init() applies data-theme attribute", () => {
    theme.init();
    expect(theme.value).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("toggles between dark and light", () => {
    theme.toggle();
    expect(theme.value).toBe("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
    theme.toggle();
    expect(theme.value).toBe("dark");
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });

  it("persists choice to localStorage", () => {
    theme.set("light");
    expect(store.get("openroast.theme")).toBe("light");
    theme.set("dark");
    expect(store.get("openroast.theme")).toBe("dark");
  });

  it("set() updates DOM attribute", () => {
    theme.set("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });

  it("init() picks up a saved value on later session", () => {
    store.set("openroast.theme", "light");
    theme.init();
    expect(theme.value).toBe("light");
    expect(document.documentElement.getAttribute("data-theme")).toBe("light");
  });
});
