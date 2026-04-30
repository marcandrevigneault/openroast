/**
 * Theme store — light/dark mode with localStorage persistence.
 *
 * Source of truth is the `data-theme` attribute on <html>; CSS variables
 * defined in +layout.svelte react to it. This module exposes a Svelte
 * rune-backed getter/setter so any component can read or toggle the
 * current theme.
 */

export type Theme = "light" | "dark";

const STORAGE_KEY = "openroast.theme";

function readSaved(): Theme | null {
  try {
    const v = globalThis.localStorage?.getItem(STORAGE_KEY);
    return v === "light" || v === "dark" ? v : null;
  } catch {
    return null;
  }
}

function writeSaved(value: Theme): void {
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, value);
  } catch {
    // localStorage unavailable (private mode, SSR) — silently skip.
  }
}

function detectInitial(): Theme {
  const saved = readSaved();
  if (saved) return saved;
  try {
    if (globalThis.matchMedia?.("(prefers-color-scheme: light)").matches) {
      return "light";
    }
  } catch {
    // matchMedia unavailable — fall through.
  }
  return "dark";
}

function applyToDocument(value: Theme): void {
  if (typeof document === "undefined") return;
  document.documentElement.setAttribute("data-theme", value);
}

let current = $state<Theme>(detectInitial());

export const theme = {
  get value(): Theme {
    return current;
  },
  set(next: Theme): void {
    current = next;
    writeSaved(next);
    applyToDocument(next);
  },
  toggle(): void {
    this.set(current === "dark" ? "light" : "dark");
  },
  init(): void {
    // Re-read storage in case it was set after module load, then apply.
    const saved = readSaved();
    if (saved && saved !== current) current = saved;
    applyToDocument(current);
  },
};
