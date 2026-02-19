import { describe, it, expect } from "vitest";
import { render } from "@testing-library/svelte";
import RoastChart from "./RoastChart.svelte";
import type {
  TemperaturePoint,
  ControlPoint,
  ControlConfig,
} from "$lib/stores/machine";
import { DEFAULT_CHART_OPTIONS } from "$lib/stores/chart-options";

function makePoints(count: number): TemperaturePoint[] {
  return Array.from({ length: count }, (_, i) => ({
    timestamp_ms: i * 1000,
    et: 200 + i * 0.5,
    bt: 160 + i * 0.8,
    et_ror: 5 + i * 0.1,
    bt_ror: 8 + i * 0.1,
  }));
}

function makeControlPoints(count: number): ControlPoint[] {
  return Array.from({ length: count }, (_, i) => ({
    timestamp_ms: i * 1000,
    values: { burner: 70 + i, airflow: 50 },
  }));
}

const TEST_CONTROLS: ControlConfig[] = [
  { name: "Burner", channel: "burner", min: 0, max: 100, step: 5, unit: "%" },
  { name: "Airflow", channel: "airflow", min: 0, max: 100, step: 5, unit: "%" },
];

describe("RoastChart", () => {
  it("renders SVG element", () => {
    const { container } = render(RoastChart, { props: { history: [] } });
    const svg = container.querySelector("svg");
    expect(svg).toBeTruthy();
  });

  it("renders background rect", () => {
    const { container } = render(RoastChart, { props: { history: [] } });
    const rects = container.querySelectorAll("rect");
    expect(rects.length).toBeGreaterThan(0);
  });

  it("renders temperature grid lines", () => {
    const { container } = render(RoastChart, { props: { history: [] } });
    const lines = container.querySelectorAll("line");
    expect(lines.length).toBeGreaterThan(2);
  });

  it("renders ET and BT paths with data", () => {
    const { container } = render(RoastChart, {
      props: { history: makePoints(20) },
    });
    const paths = container.querySelectorAll("path");
    expect(paths.length).toBe(2);
  });

  it("renders no paths when history is empty", () => {
    const { container } = render(RoastChart, { props: { history: [] } });
    const paths = container.querySelectorAll("path");
    expect(paths.length).toBe(0);
  });

  it("renders current value markers with data", () => {
    const { container } = render(RoastChart, {
      props: { history: makePoints(5) },
    });
    const circles = container.querySelectorAll("circle");
    expect(circles.length).toBe(2);
  });

  it("renders dynamic legend", () => {
    const { container } = render(RoastChart, { props: { history: [] } });
    const texts = container.querySelectorAll("text");
    const textContent = Array.from(texts).map((t) => t.textContent);
    expect(textContent).toContain("ET");
    expect(textContent).toContain("BT");
  });

  it("respects custom width and height", () => {
    const { container } = render(RoastChart, {
      props: { history: [], width: 600, height: 250 },
    });
    const svg = container.querySelector("svg");
    expect(svg?.getAttribute("width")).toBe("600");
    expect(svg?.getAttribute("height")).toBe("250");
  });

  it("hides ET path when showET is false", () => {
    const opts = { ...DEFAULT_CHART_OPTIONS, showET: false };
    const { container } = render(RoastChart, {
      props: { history: makePoints(20), options: opts },
    });
    const paths = container.querySelectorAll("path");
    // Only BT path should render
    expect(paths.length).toBe(1);
  });

  it("hides BT path when showBT is false", () => {
    const opts = { ...DEFAULT_CHART_OPTIONS, showBT: false };
    const { container } = render(RoastChart, {
      props: { history: makePoints(20), options: opts },
    });
    const paths = container.querySelectorAll("path");
    expect(paths.length).toBe(1);
  });

  it("shows RoR paths when enabled", () => {
    const opts = {
      ...DEFAULT_CHART_OPTIONS,
      showETRor: true,
      showBTRor: true,
    };
    const { container } = render(RoastChart, {
      props: { history: makePoints(20), options: opts },
    });
    const paths = container.querySelectorAll("path");
    // ET + BT + ET RoR + BT RoR = 4 paths
    expect(paths.length).toBe(4);
  });

  it("shows control paths when enabled", () => {
    const opts = {
      ...DEFAULT_CHART_OPTIONS,
      showControls: { burner: true, airflow: true },
    };
    const { container } = render(RoastChart, {
      props: {
        history: makePoints(20),
        controlHistory: makeControlPoints(20),
        controls: TEST_CONTROLS,
        options: opts,
      },
    });
    const paths = container.querySelectorAll("path");
    // ET + BT + Burner + Airflow = 4 paths
    expect(paths.length).toBe(4);
  });

  it("shows right Y-axis when RoR or controls enabled", () => {
    const opts = { ...DEFAULT_CHART_OPTIONS, showETRor: true };
    const { container } = render(RoastChart, {
      props: { history: makePoints(20), options: opts },
    });
    const texts = container.querySelectorAll("text");
    const textContent = Array.from(texts).map((t) => t.textContent?.trim());
    expect(textContent).toContain("0");
    expect(textContent).toContain("100");
  });

  it("hides right Y-axis when no secondary curves enabled", () => {
    const { container } = render(RoastChart, {
      props: { history: makePoints(5) },
    });
    const texts = container.querySelectorAll("text");
    const textContent = Array.from(texts).map((t) => t.textContent?.trim());
    // Right axis labels (0, 25, 50, 75, 100) should not be present
    // when no RoR or controls enabled. Check for "75" which only appears on right axis.
    expect(textContent).not.toContain("75");
  });

  it("legend shows only visible curves", () => {
    const opts = {
      ...DEFAULT_CHART_OPTIONS,
      showET: true,
      showBT: false,
      showControls: { burner: true },
    };
    const { container } = render(RoastChart, {
      props: {
        history: [],
        controls: TEST_CONTROLS,
        options: opts,
      },
    });
    const texts = container.querySelectorAll("text");
    const legendTexts = Array.from(texts)
      .map((t) => t.textContent?.trim())
      .filter((t) => t === "ET" || t === "BT" || t === "Burner");
    expect(legendTexts).toContain("ET");
    expect(legendTexts).toContain("Burner");
    expect(legendTexts).not.toContain("BT");
  });
});
