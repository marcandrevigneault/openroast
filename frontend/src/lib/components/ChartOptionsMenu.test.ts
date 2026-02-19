import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import ChartOptionsMenu from "./ChartOptionsMenu.svelte";
import {
  DEFAULT_CHART_OPTIONS,
  type ChartOptions,
} from "$lib/stores/chart-options";

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
    // No checkboxes visible
    expect(screen.queryAllByRole("checkbox")).toHaveLength(0);
  });

  it("shows popover when gear clicked", async () => {
    const onchange = vi.fn();
    render(ChartOptionsMenu, {
      props: { options: { ...DEFAULT_CHART_OPTIONS }, onchange },
    });
    await fireEvent.click(screen.getByLabelText("Chart options"));
    // Should show 7 checkboxes
    expect(screen.getAllByRole("checkbox")).toHaveLength(7);
  });

  it("shows all curve labels in popover", async () => {
    const onchange = vi.fn();
    render(ChartOptionsMenu, {
      props: { options: { ...DEFAULT_CHART_OPTIONS }, onchange },
    });
    await fireEvent.click(screen.getByLabelText("Chart options"));
    expect(screen.getByText("ET")).toBeInTheDocument();
    expect(screen.getByText("BT")).toBeInTheDocument();
    expect(screen.getByText("ET RoR")).toBeInTheDocument();
    expect(screen.getByText("BT RoR")).toBeInTheDocument();
    expect(screen.getByText("Burner")).toBeInTheDocument();
    expect(screen.getByText("Airflow")).toBeInTheDocument();
    expect(screen.getByText("Drum")).toBeInTheDocument();
  });

  it("calls onchange when checkbox toggled", async () => {
    const onchange = vi.fn();
    render(ChartOptionsMenu, {
      props: { options: { ...DEFAULT_CHART_OPTIONS }, onchange },
    });
    await fireEvent.click(screen.getByLabelText("Chart options"));
    const checkboxes = screen.getAllByRole("checkbox");
    // Toggle the 3rd checkbox (ET RoR, index 2)
    await fireEvent.change(checkboxes[2]);
    expect(onchange).toHaveBeenCalledOnce();
    const updated = onchange.mock.calls[0][0] as ChartOptions;
    expect(updated.showETRor).toBe(true);
  });

  it("reflects checked state from options", async () => {
    const onchange = vi.fn();
    const opts = { ...DEFAULT_CHART_OPTIONS, showBurner: true };
    render(ChartOptionsMenu, { props: { options: opts, onchange } });
    await fireEvent.click(screen.getByLabelText("Chart options"));
    const checkboxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    // Burner is index 4
    expect(checkboxes[4].checked).toBe(true);
  });
});
