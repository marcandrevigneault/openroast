import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  addToast,
  dismissToast,
  clearToasts,
  getToasts,
  subscribe,
} from "./toast";

describe("toast store", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    clearToasts();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("starts with no toasts", () => {
    expect(getToasts()).toEqual([]);
  });

  it("adds a toast with default error type", () => {
    addToast("Something failed");
    const toasts = getToasts();
    expect(toasts).toHaveLength(1);
    expect(toasts[0].message).toBe("Something failed");
    expect(toasts[0].type).toBe("error");
  });

  it("adds a toast with custom type", () => {
    addToast("Heads up", "warning");
    expect(getToasts()[0].type).toBe("warning");
  });

  it("adds a toast with machine label", () => {
    addToast("Lost connection", "error", "Stratto 2.0");
    expect(getToasts()[0].machineLabel).toBe("Stratto 2.0");
  });

  it("returns unique IDs", () => {
    const id1 = addToast("A");
    const id2 = addToast("B");
    expect(id1).not.toBe(id2);
  });

  it("dismisses a toast by ID", () => {
    const id = addToast("A");
    addToast("B");
    dismissToast(id);
    expect(getToasts()).toHaveLength(1);
    expect(getToasts()[0].message).toBe("B");
  });

  it("clears all toasts", () => {
    addToast("A");
    addToast("B");
    clearToasts();
    expect(getToasts()).toEqual([]);
  });

  it("auto-dismisses after 6 seconds", () => {
    addToast("Temp");
    expect(getToasts()).toHaveLength(1);
    vi.advanceTimersByTime(6000);
    expect(getToasts()).toHaveLength(0);
  });

  it("notifies subscribers on add", () => {
    const fn = vi.fn();
    const unsub = subscribe(fn);
    addToast("A");
    expect(fn).toHaveBeenCalledOnce();
    unsub();
  });

  it("notifies subscribers on dismiss", () => {
    const id = addToast("A");
    const fn = vi.fn();
    const unsub = subscribe(fn);
    dismissToast(id);
    expect(fn).toHaveBeenCalledOnce();
    unsub();
  });

  it("unsubscribe stops notifications", () => {
    const fn = vi.fn();
    const unsub = subscribe(fn);
    unsub();
    addToast("A");
    expect(fn).not.toHaveBeenCalled();
  });
});
