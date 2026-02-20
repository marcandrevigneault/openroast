import { describe, it, expect } from "vitest";
import {
  DEFAULT_CHART_OPTIONS,
  createChartOptions,
  smoothRor,
  type ChartOptions,
} from "./chart-options";

describe("DEFAULT_CHART_OPTIONS", () => {
  it("shows ET and BT by default", () => {
    expect(DEFAULT_CHART_OPTIONS.showET).toBe(true);
    expect(DEFAULT_CHART_OPTIONS.showBT).toBe(true);
  });

  it("hides RoR curves by default", () => {
    expect(DEFAULT_CHART_OPTIONS.showETRor).toBe(false);
    expect(DEFAULT_CHART_OPTIONS.showBTRor).toBe(false);
  });

  it("has empty control and extra channel maps by default", () => {
    expect(DEFAULT_CHART_OPTIONS.showControls).toEqual({});
    expect(DEFAULT_CHART_OPTIONS.showExtraChannels).toEqual({});
  });

  it("defaults rorSmoothing to 1", () => {
    expect(DEFAULT_CHART_OPTIONS.rorSmoothing).toBe(1);
  });

  it("has all expected fields", () => {
    const keys = Object.keys(DEFAULT_CHART_OPTIONS);
    expect(keys).toContain("showET");
    expect(keys).toContain("showBT");
    expect(keys).toContain("showETRor");
    expect(keys).toContain("showBTRor");
    expect(keys).toContain("showControls");
    expect(keys).toContain("showExtraChannels");
    expect(keys).toContain("rorSmoothing");
  });

  it("can be spread to create a copy", () => {
    const copy: ChartOptions = { ...DEFAULT_CHART_OPTIONS, showETRor: true };
    expect(copy.showETRor).toBe(true);
    expect(DEFAULT_CHART_OPTIONS.showETRor).toBe(false);
  });
});

describe("createChartOptions", () => {
  it("creates options with controls defaulting to visible", () => {
    const opts = createChartOptions(["burner", "airflow"], []);
    expect(opts.showControls.burner).toBe(true);
    expect(opts.showControls.airflow).toBe(true);
  });

  it("creates options with extra channels defaulting to visible", () => {
    const opts = createChartOptions([], ["Inlet", "Exhaust"]);
    expect(opts.showExtraChannels.Inlet).toBe(true);
    expect(opts.showExtraChannels.Exhaust).toBe(true);
  });

  it("creates options with both controls and extra channels", () => {
    const opts = createChartOptions(["burner"], ["Inlet"]);
    expect(opts.showControls.burner).toBe(true);
    expect(opts.showExtraChannels.Inlet).toBe(true);
    expect(opts.showET).toBe(true);
    expect(opts.showBT).toBe(true);
  });

  it("creates default options when called with no args", () => {
    const opts = createChartOptions();
    expect(opts.showControls).toEqual({});
    expect(opts.showExtraChannels).toEqual({});
  });

  it("sets rorSmoothing to 1 by default", () => {
    const opts = createChartOptions(["burner"], ["Inlet"]);
    expect(opts.rorSmoothing).toBe(1);
  });
});

describe("smoothRor", () => {
  it("returns original values when windowSize is 1", () => {
    const values = [5, 10, 15, 20];
    expect(smoothRor(values, 1)).toEqual([5, 10, 15, 20]);
  });

  it("returns original values when windowSize is 0", () => {
    const values = [5, 10, 15];
    expect(smoothRor(values, 0)).toEqual([5, 10, 15]);
  });

  it("computes trailing moving average with window 3", () => {
    const values = [3, 6, 9, 12, 15];
    const result = smoothRor(values, 3);
    // i=0: avg(3) = 3
    // i=1: avg(3,6) = 4.5
    // i=2: avg(3,6,9) = 6
    // i=3: avg(6,9,12) = 9
    // i=4: avg(9,12,15) = 12
    expect(result[0]).toBe(3);
    expect(result[1]).toBe(4.5);
    expect(result[2]).toBe(6);
    expect(result[3]).toBe(9);
    expect(result[4]).toBe(12);
  });

  it("handles empty array", () => {
    expect(smoothRor([], 5)).toEqual([]);
  });

  it("handles single element", () => {
    expect(smoothRor([10], 3)).toEqual([10]);
  });
});
