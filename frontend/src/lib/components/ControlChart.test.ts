import { describe, it, expect } from "vitest";
import { render } from "@testing-library/svelte";
import ControlChart from "./ControlChart.svelte";
import type {
  TemperaturePoint,
  ControlPoint,
  ControlConfig,
  ExtraChannelConfig,
  ExtraChannelPoint,
} from "$lib/stores/machine";
import { DEFAULT_CHART_OPTIONS } from "$lib/stores/chart-options";

function makePoints(count: number): TemperaturePoint[] {
  return Array.from({ length: count }, (_, i) => ({
    timestamp_ms: i * 1000,
    et: 200 + i * 0.5,
    bt: 160 + i * 0.8,
    et_ror: 5,
    bt_ror: 8,
  }));
}

function makeControlPoints(count: number): ControlPoint[] {
  return Array.from({ length: count }, (_, i) => ({
    timestamp_ms: i * 1000,
    values: { burner: 70 + i, airflow: 50 },
  }));
}

function makeExtraChannelPoints(count: number): ExtraChannelPoint[] {
  return Array.from({ length: count }, (_, i) => ({
    timestamp_ms: i * 1000,
    values: { Burner: 70 + i, Air: 50 },
  }));
}

const TEST_CONTROLS: ControlConfig[] = [
  { name: "Burner", channel: "burner", min: 0, max: 100, step: 5, unit: "%" },
  {
    name: "Airflow",
    channel: "airflow",
    min: 0,
    max: 100,
    step: 5,
    unit: "%",
  },
];

const TEST_EXTRA_CHANNELS: ExtraChannelConfig[] = [
  { name: "Burner" },
  { name: "Air" },
];

describe("ControlChart", () => {
  it("renders nothing when no controls or extra channels are visible", () => {
    const { container } = render(ControlChart, {
      props: { history: [], controls: [], extraChannels: [] },
    });
    const svg = container.querySelector("svg");
    expect(svg).toBeNull();
  });

  it("renders SVG when extra channels are visible", () => {
    const opts = {
      ...DEFAULT_CHART_OPTIONS,
      showExtraChannels: { Burner: true, Air: true },
    };
    const { container } = render(ControlChart, {
      props: {
        history: makePoints(10),
        extraChannelHistory: makeExtraChannelPoints(10),
        extraChannels: TEST_EXTRA_CHANNELS,
        controls: TEST_CONTROLS,
        options: opts,
      },
    });
    const svg = container.querySelector("svg");
    expect(svg).toBeTruthy();
  });

  it("renders control paths when enabled", () => {
    const opts = {
      ...DEFAULT_CHART_OPTIONS,
      showControls: { burner: true, airflow: true },
    };
    const { container } = render(ControlChart, {
      props: {
        history: makePoints(10),
        controlHistory: makeControlPoints(10),
        controls: TEST_CONTROLS,
        extraChannels: [],
        options: opts,
      },
    });
    const paths = container.querySelectorAll("path");
    // Burner + Airflow = 2 paths
    expect(paths.length).toBe(2);
  });

  it("shows legend entries for visible curves", () => {
    const opts = {
      ...DEFAULT_CHART_OPTIONS,
      showExtraChannels: { Burner: true },
    };
    const { container } = render(ControlChart, {
      props: {
        history: makePoints(10),
        extraChannelHistory: makeExtraChannelPoints(10),
        extraChannels: TEST_EXTRA_CHANNELS,
        controls: TEST_CONTROLS,
        options: opts,
      },
    });
    const texts = container.querySelectorAll("text");
    const textContent = Array.from(texts).map((t) => t.textContent?.trim());
    expect(textContent).toContain("Burner");
  });

  it("renders Y-axis with 0-100 scale", () => {
    const opts = {
      ...DEFAULT_CHART_OPTIONS,
      showExtraChannels: { Burner: true },
    };
    const { container } = render(ControlChart, {
      props: {
        history: makePoints(10),
        extraChannelHistory: makeExtraChannelPoints(10),
        extraChannels: TEST_EXTRA_CHANNELS,
        controls: TEST_CONTROLS,
        options: opts,
      },
    });
    const texts = container.querySelectorAll("text");
    const textContent = Array.from(texts).map((t) => t.textContent?.trim());
    expect(textContent).toContain("0");
    expect(textContent).toContain("50");
    expect(textContent).toContain("100");
  });
});
