import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render } from "@testing-library/svelte";
import RoastTimer from "./RoastTimer.svelte";

describe("RoastTimer", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("displays 00:00 when idle", () => {
    const { container } = render(RoastTimer, {
      props: { sessionState: "idle" },
    });
    expect(container.textContent).toContain("00:00");
  });

  it("displays 00:00 when monitoring (not ticking)", async () => {
    const { container } = render(RoastTimer, {
      props: { sessionState: "monitoring" },
    });
    await vi.advanceTimersByTimeAsync(0);
    expect(container.textContent).toContain("00:00");

    await vi.advanceTimersByTimeAsync(3000);
    // Still 00:00 — monitoring does not tick.
    expect(container.textContent).toContain("00:00");
  });

  it("ticks once per second while recording", async () => {
    const { container } = render(RoastTimer, {
      props: { sessionState: "recording" },
    });
    await vi.advanceTimersByTimeAsync(0);
    expect(container.textContent).toContain("00:00");

    await vi.advanceTimersByTimeAsync(1000);
    expect(container.textContent).toContain("00:01");

    await vi.advanceTimersByTimeAsync(4000);
    expect(container.textContent).toContain("00:05");
  });

  it("formats minutes correctly past 60s", async () => {
    const { container } = render(RoastTimer, {
      props: { sessionState: "recording" },
    });
    await vi.advanceTimersByTimeAsync(75 * 1000);
    expect(container.textContent).toContain("01:15");
  });

  it("resets to 00:00 on transition recording → monitoring", async () => {
    const { container, rerender } = render(RoastTimer, {
      props: { sessionState: "recording" },
    });
    await vi.advanceTimersByTimeAsync(5000);
    expect(container.textContent).toContain("00:05");

    await rerender({ sessionState: "monitoring" });
    await vi.advanceTimersByTimeAsync(0);
    expect(container.textContent).toContain("00:00");
  });

  it("freezes value when recording → finished", async () => {
    const { container, rerender } = render(RoastTimer, {
      props: { sessionState: "recording" },
    });
    await vi.advanceTimersByTimeAsync(7000);
    expect(container.textContent).toContain("00:07");

    await rerender({ sessionState: "finished" });
    await vi.advanceTimersByTimeAsync(5000);
    // Frozen at 00:07
    expect(container.textContent).toContain("00:07");
  });

  it("restarts from 00:00 on a new recording", async () => {
    const { container, rerender } = render(RoastTimer, {
      props: { sessionState: "recording" },
    });
    await vi.advanceTimersByTimeAsync(10 * 1000);
    expect(container.textContent).toContain("00:10");

    await rerender({ sessionState: "monitoring" });
    await vi.advanceTimersByTimeAsync(0);
    expect(container.textContent).toContain("00:00");

    await rerender({ sessionState: "recording" });
    await vi.advanceTimersByTimeAsync(2000);
    expect(container.textContent).toContain("00:02");
  });

  it("adds an active class to the value while recording", () => {
    const { container } = render(RoastTimer, {
      props: { sessionState: "recording" },
    });
    expect(container.querySelector(".timer.active")).not.toBeNull();
  });

  it("does not have active class when idle", () => {
    const { container } = render(RoastTimer, {
      props: { sessionState: "idle" },
    });
    expect(container.querySelector(".timer.active")).toBeNull();
  });
});
