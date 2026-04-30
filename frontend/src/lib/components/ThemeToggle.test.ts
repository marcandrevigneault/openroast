import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import ThemeToggle from "./ThemeToggle.svelte";
import { theme } from "$lib/stores/theme.svelte";

const store = new Map<string, string>();
vi.stubGlobal("localStorage", {
  getItem: vi.fn((k: string) => store.get(k) ?? null),
  setItem: vi.fn((k: string, v: string) => store.set(k, v)),
  removeItem: vi.fn((k: string) => store.delete(k)),
  clear: vi.fn(() => store.clear()),
  length: 0,
  key: vi.fn(() => null),
});

describe("ThemeToggle", () => {
  beforeEach(() => {
    store.clear();
    theme.set("dark");
  });

  it("renders a toggle button with an aria-label", () => {
    const { getByRole } = render(ThemeToggle);
    const btn = getByRole("button");
    expect(btn.getAttribute("aria-label")).toMatch(/light theme/i);
  });

  it("flips theme on click", async () => {
    const { getByRole } = render(ThemeToggle);
    const btn = getByRole("button");
    expect(theme.value).toBe("dark");
    await fireEvent.click(btn);
    expect(theme.value).toBe("light");
    await fireEvent.click(btn);
    expect(theme.value).toBe("dark");
  });

  it("updates aria-label after toggling", async () => {
    const { getByRole } = render(ThemeToggle);
    const btn = getByRole("button");
    await fireEvent.click(btn);
    expect(btn.getAttribute("aria-label")).toMatch(/dark theme/i);
  });
});
