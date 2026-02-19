import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import DashboardToolbar from "./DashboardToolbar.svelte";
import type { LayoutConfig } from "$lib/stores/dashboard";

const defaultLayout: LayoutConfig = { mode: "grid", columns: 2 };

describe("DashboardToolbar", () => {
  it("renders Add Machine button", () => {
    render(DashboardToolbar, {
      props: {
        layout: defaultLayout,
        machineCount: 0,
        onaddmachine: () => {},
        onlayoutchange: () => {},
      },
    });
    expect(screen.getByText("+ Add Machine")).toBeInTheDocument();
  });

  it("calls onaddmachine when button clicked", async () => {
    const onaddmachine = vi.fn();
    render(DashboardToolbar, {
      props: {
        layout: defaultLayout,
        machineCount: 0,
        onaddmachine,
        onlayoutchange: () => {},
      },
    });
    await fireEvent.click(screen.getByText("+ Add Machine"));
    expect(onaddmachine).toHaveBeenCalledOnce();
  });

  it("renders layout mode buttons", () => {
    render(DashboardToolbar, {
      props: {
        layout: defaultLayout,
        machineCount: 1,
        onaddmachine: () => {},
        onlayoutchange: () => {},
      },
    });
    expect(screen.getByTitle("Grid")).toBeInTheDocument();
    expect(screen.getByTitle("Side by side")).toBeInTheDocument();
    expect(screen.getByTitle("Stacked")).toBeInTheDocument();
  });

  it("highlights active layout mode", () => {
    const { container } = render(DashboardToolbar, {
      props: {
        layout: { mode: "vertical", columns: 2 },
        machineCount: 1,
        onaddmachine: () => {},
        onlayoutchange: () => {},
      },
    });
    const activeBtn = container.querySelector(".layout-btn.active");
    expect(activeBtn).toBeTruthy();
    expect(activeBtn?.getAttribute("title")).toBe("Stacked");
  });

  it("calls onlayoutchange when mode clicked", async () => {
    const onlayoutchange = vi.fn();
    render(DashboardToolbar, {
      props: {
        layout: defaultLayout,
        machineCount: 1,
        onaddmachine: () => {},
        onlayoutchange,
      },
    });
    await fireEvent.click(screen.getByTitle("Stacked"));
    expect(onlayoutchange).toHaveBeenCalledWith({ mode: "vertical" });
  });

  it("shows column selector in grid mode", () => {
    const { container } = render(DashboardToolbar, {
      props: {
        layout: { mode: "grid", columns: 2 },
        machineCount: 1,
        onaddmachine: () => {},
        onlayoutchange: () => {},
      },
    });
    expect(container.querySelector(".col-select")).toBeTruthy();
  });

  it("hides column selector in non-grid mode", () => {
    const { container } = render(DashboardToolbar, {
      props: {
        layout: { mode: "horizontal", columns: 2 },
        machineCount: 1,
        onaddmachine: () => {},
        onlayoutchange: () => {},
      },
    });
    expect(container.querySelector(".col-select")).toBeFalsy();
  });

  it("displays machine count singular", () => {
    render(DashboardToolbar, {
      props: {
        layout: defaultLayout,
        machineCount: 1,
        onaddmachine: () => {},
        onlayoutchange: () => {},
      },
    });
    expect(screen.getByText("1 machine")).toBeInTheDocument();
  });

  it("displays machine count plural", () => {
    render(DashboardToolbar, {
      props: {
        layout: defaultLayout,
        machineCount: 3,
        onaddmachine: () => {},
        onlayoutchange: () => {},
      },
    });
    expect(screen.getByText("3 machines")).toBeInTheDocument();
  });
});
