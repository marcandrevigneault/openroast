import { describe, it, expect } from "vitest";
import { DEFAULT_CHART_OPTIONS, type ChartOptions } from "./chart-options";

describe("DEFAULT_CHART_OPTIONS", () => {
  it("shows ET and BT by default", () => {
    expect(DEFAULT_CHART_OPTIONS.showET).toBe(true);
    expect(DEFAULT_CHART_OPTIONS.showBT).toBe(true);
  });

  it("hides RoR curves by default", () => {
    expect(DEFAULT_CHART_OPTIONS.showETRor).toBe(false);
    expect(DEFAULT_CHART_OPTIONS.showBTRor).toBe(false);
  });

  it("hides control curves by default", () => {
    expect(DEFAULT_CHART_OPTIONS.showBurner).toBe(false);
    expect(DEFAULT_CHART_OPTIONS.showAirflow).toBe(false);
    expect(DEFAULT_CHART_OPTIONS.showDrum).toBe(false);
  });

  it("has all 7 option fields", () => {
    const keys = Object.keys(DEFAULT_CHART_OPTIONS);
    expect(keys).toHaveLength(7);
  });

  it("can be spread to create a copy", () => {
    const copy: ChartOptions = { ...DEFAULT_CHART_OPTIONS, showETRor: true };
    expect(copy.showETRor).toBe(true);
    expect(DEFAULT_CHART_OPTIONS.showETRor).toBe(false);
  });
});
