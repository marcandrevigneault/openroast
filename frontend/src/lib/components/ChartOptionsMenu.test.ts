import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import ChartOptionsMenu from "./ChartOptionsMenu.svelte";
import {
  DEFAULT_CHART_OPTIONS,
  type ChartOptions,
} from "$lib/stores/chart-options";
import type { ControlConfig, ExtraChannelConfig } from "$lib/stores/machine";

const TEST_CONTROLS: ControlConfig[] = [
  { name: "Burner", channel: "burner", min: 0, max: 100, step: 5, unit: "%" },
  { name: "Airflow", channel: "airflow", min: 0, max: 100, step: 5, unit: "%" },
  { name: "Drum", channel: "drum", min: 0, max: 100, step: 5, unit: "" },
];

const TEST_EXTRA_CHANNELS: ExtraChannelConfig[] = [{ name: "Inlet" }];

describe("ChartOptionsMenu", () => {
  it("renders gear button", () => {
    const onchange = vi.fn();
    render(ChartOptionsMenu, {
      props: { options: { ...DEFAULT_CHART_OPTIONS }, onchange },
    });
    expect(screen.getByLabelText("Chart options")).toBeInTheDocument();
  });

  it("popover hidden initially", () => {
    const onchange = vi.fn();
    render(ChartOptionsMenu, {
      props: { options: { ...DEFAULT_CHART_OPTIONS }, onchange },
    });
    expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
  });

  it("shows base checkboxes when gear clicked (no controls)", async () => {
    const onchange = vi.fn();
    render(ChartOptionsMenu, {
      props: { options: { ...DEFAULT_CHART_OPTIONS }, onchange },
    });
    await fireEvent.click(screen.getByLabelText("Chart options"));
    // 4 base checkboxes: ET, BT, ET RoR, BT RoR
    expect(screen.getAllByRole("checkbox")).toHaveLength(4);
  });

  it("shows control checkboxes when controls provided", async () => {
    const onchange = vi.fn();
    render(ChartOptionsMenu, {
      props: {
        options: { ...DEFAULT_CHART_OPTIONS },
        controls: TEST_CONTROLS,
        onchange,
      },
    });
    await fireEvent.click(screen.getByLabelText("Chart options"));
    // 4 base + 3 controls = 7
    expect(screen.getAllByRole("checkbox")).toHaveLength(7);
    expect(screen.getByText("Burner")).toBeInTheDocument();
    expect(screen.getByText("Airflow")).toBeInTheDocument();
    expect(screen.getByText("Drum")).toBeInTheDocument();
  });

  it("shows extra channel checkboxes when provided", async () => {
    const onchange = vi.fn();
    render(ChartOptionsMenu, {
      props: {
        options: { ...DEFAULT_CHART_OPTIONS },
        controls: TEST_CONTROLS,
        extraChannels: TEST_EXTRA_CHANNELS,
        onchange,
      },
    });
    await fireEvent.click(screen.getByLabelText("Chart options"));
    // 4 base + 3 controls + 1 extra channel = 8
    expect(screen.getAllByRole("checkbox")).toHaveLength(8);
    expect(screen.getByText("Inlet")).toBeInTheDocument();
  });

  it("shows base curve labels in popover", async () => {
    const onchange = vi.fn();
    render(ChartOptionsMenu, {
      props: { options: { ...DEFAULT_CHART_OPTIONS }, onchange },
    });
    await fireEvent.click(screen.getByLabelText("Chart options"));
    expect(screen.getByText("ET")).toBeInTheDocument();
    expect(screen.getByText("BT")).toBeInTheDocument();
    expect(screen.getByText("ET RoR")).toBeInTheDocument();
    expect(screen.getByText("BT RoR")).toBeInTheDocument();
  });

  it("calls onchange when base checkbox toggled", async () => {
    const onchange = vi.fn();
    render(ChartOptionsMenu, {
      props: { options: { ...DEFAULT_CHART_OPTIONS }, onchange },
    });
    await fireEvent.click(screen.getByLabelText("Chart options"));
    const checkboxes = screen.getAllByRole("checkbox");
    // Toggle ET RoR (index 2)
    await fireEvent.change(checkboxes[2]);
    expect(onchange).toHaveBeenCalledOnce();
    const updated = onchange.mock.calls[0][0] as ChartOptions;
    expect(updated.showETRor).toBe(true);
  });

  it("calls onchange when control checkbox toggled", async () => {
    const onchange = vi.fn();
    const opts: ChartOptions = {
      ...DEFAULT_CHART_OPTIONS,
      showControls: { burner: false, airflow: false, drum: false },
    };
    render(ChartOptionsMenu, {
      props: { options: opts, controls: TEST_CONTROLS, onchange },
    });
    await fireEvent.click(screen.getByLabelText("Chart options"));
    const checkboxes = screen.getAllByRole("checkbox");
    // Toggle Burner (index 4, after 4 base items)
    await fireEvent.change(checkboxes[4]);
    expect(onchange).toHaveBeenCalledOnce();
    const updated = onchange.mock.calls[0][0] as ChartOptions;
    expect(updated.showControls.burner).toBe(true);
  });
});
