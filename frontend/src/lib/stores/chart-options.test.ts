import { describe, it, expect } from "vitest";
import {
  DEFAULT_CHART_OPTIONS,
  createChartOptions,
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

  it("has all expected fields", () => {
    const keys = Object.keys(DEFAULT_CHART_OPTIONS);
    expect(keys).toContain("showET");
    expect(keys).toContain("showBT");
    expect(keys).toContain("showETRor");
    expect(keys).toContain("showBTRor");
    expect(keys).toContain("showControls");
    expect(keys).toContain("showExtraChannels");
  });

  it("can be spread to create a copy", () => {
    const copy: ChartOptions = { ...DEFAULT_CHART_OPTIONS, showETRor: true };
    expect(copy.showETRor).toBe(true);
    expect(DEFAULT_CHART_OPTIONS.showETRor).toBe(false);
  });
});

describe("createChartOptions", () => {
  it("creates options with controls defaulting to hidden", () => {
    const opts = createChartOptions(["burner", "airflow"], []);
    expect(opts.showControls.burner).toBe(false);
    expect(opts.showControls.airflow).toBe(false);
  });

  it("creates options with extra channels defaulting to hidden", () => {
    const opts = createChartOptions([], ["Inlet", "Exhaust"]);
    expect(opts.showExtraChannels.Inlet).toBe(false);
    expect(opts.showExtraChannels.Exhaust).toBe(false);
  });

  it("creates options with both controls and extra channels", () => {
    const opts = createChartOptions(["burner"], ["Inlet"]);
    expect(opts.showControls.burner).toBe(false);
    expect(opts.showExtraChannels.Inlet).toBe(false);
    expect(opts.showET).toBe(true);
    expect(opts.showBT).toBe(true);
  });

  it("creates default options when called with no args", () => {
    const opts = createChartOptions();
    expect(opts.showControls).toEqual({});
    expect(opts.showExtraChannels).toEqual({});
  });
});
