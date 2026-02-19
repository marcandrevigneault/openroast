import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import MachinePanel from "./MachinePanel.svelte";
import {
  createInitialState,
  type MachineState,
  type ControlConfig,
} from "$lib/stores/machine";

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
  { name: "Drum", channel: "drum", min: 0, max: 100, step: 5, unit: "" },
];

function makeMachine(overrides: Partial<MachineState> = {}): MachineState {
  return {
    ...createInitialState("m1", "Test Roaster", TEST_CONTROLS),
    driverState: "connected",
    sessionState: "monitoring",
    ...overrides,
  };
}

describe("MachinePanel", () => {
  it("renders machine name", () => {
    render(MachinePanel, { props: { machine: makeMachine() } });
    expect(screen.getByText("Test Roaster")).toBeInTheDocument();
  });

  it("renders connection status", () => {
    render(MachinePanel, { props: { machine: makeMachine() } });
    expect(screen.getByText("Monitoring")).toBeInTheDocument();
  });

  it("renders session controls", () => {
    render(MachinePanel, {
      props: { machine: makeMachine({ sessionState: "idle" }) },
    });
    expect(screen.getByText(/Monitor/)).toBeInTheDocument();
  });

  it("renders compact temperature displays in header", () => {
    render(MachinePanel, {
      props: {
        machine: makeMachine({
          currentTemp: {
            timestamp_ms: 1000,
            et: 215.3,
            bt: 190.7,
            et_ror: 6.5,
            bt_ror: 11.2,
          },
        }),
      },
    });
    expect(screen.getAllByText("ET").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("BT").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("215.3")).toBeInTheDocument();
    expect(screen.getByText("190.7")).toBeInTheDocument();
  });

  it("shows controls toggle button", () => {
    render(MachinePanel, { props: { machine: makeMachine() } });
    expect(screen.getByText("Controls")).toBeInTheDocument();
  });

  it("hides sliders by default (collapsed)", () => {
    const { container } = render(MachinePanel, {
      props: { machine: makeMachine() },
    });
    const sliders = container.querySelectorAll('input[type="range"]');
    expect(sliders).toHaveLength(0);
  });

  it("shows sliders when controls toggle is clicked", async () => {
    const { container } = render(MachinePanel, {
      props: { machine: makeMachine() },
    });
    await fireEvent.click(screen.getByText("Controls"));
    const sliders = container.querySelectorAll('input[type="range"]');
    expect(sliders).toHaveLength(3);
  });

  it("shows slider labels when expanded", async () => {
    render(MachinePanel, { props: { machine: makeMachine() } });
    await fireEvent.click(screen.getByText("Controls"));
    expect(screen.getByText("Burner")).toBeInTheDocument();
    expect(screen.getByText("Airflow")).toBeInTheDocument();
    expect(screen.getByText("Drum")).toBeInTheDocument();
  });

  it("hides controls section when no controls configured", () => {
    const machine = makeMachine({ controls: [] });
    render(MachinePanel, { props: { machine } });
    expect(screen.queryByText("Controls")).not.toBeInTheDocument();
  });

  it("renders event buttons", () => {
    render(MachinePanel, {
      props: { machine: makeMachine({ sessionState: "recording" }) },
    });
    expect(screen.getByText("CHARGE")).toBeInTheDocument();
    expect(screen.getByText("DROP")).toBeInTheDocument();
  });

  it("shows error banner when error exists", () => {
    render(MachinePanel, {
      props: { machine: makeMachine({ error: "Connection lost" }) },
    });
    expect(screen.getByText("Connection lost")).toBeInTheDocument();
  });

  it("hides error banner when no error", () => {
    render(MachinePanel, {
      props: { machine: makeMachine({ error: null }) },
    });
    expect(screen.queryByText("Connection lost")).not.toBeInTheDocument();
  });

  it("renders chart", () => {
    const { container } = render(MachinePanel, {
      props: { machine: makeMachine() },
    });
    expect(container.querySelector("svg")).toBeTruthy();
  });

  it("enables sliders when connected", async () => {
    const { container } = render(MachinePanel, {
      props: {
        machine: makeMachine({
          sessionState: "idle",
          driverState: "connected",
        }),
      },
    });
    await fireEvent.click(screen.getByText("Controls"));
    const sliders = container.querySelectorAll('input[type="range"]');
    sliders.forEach((slider) => {
      expect(slider).not.toBeDisabled();
    });
  });

  it("disables sliders when disconnected", async () => {
    const { container } = render(MachinePanel, {
      props: { machine: makeMachine({ driverState: "disconnected" }) },
    });
    await fireEvent.click(screen.getByText("Controls"));
    const sliders = container.querySelectorAll('input[type="range"]');
    sliders.forEach((slider) => {
      expect(slider).toBeDisabled();
    });
  });

  it("shows remove button when onremove provided", () => {
    render(MachinePanel, {
      props: { machine: makeMachine(), onremove: () => {} },
    });
    expect(screen.getByTitle("Remove machine")).toBeInTheDocument();
  });

  it("hides remove button when onremove not provided", () => {
    render(MachinePanel, {
      props: { machine: makeMachine() },
    });
    expect(screen.queryByTitle("Remove machine")).not.toBeInTheDocument();
  });

  it("calls onremove when remove button clicked", async () => {
    const onremove = vi.fn();
    render(MachinePanel, {
      props: { machine: makeMachine(), onremove },
    });
    await fireEvent.click(screen.getByTitle("Remove machine"));
    expect(onremove).toHaveBeenCalledOnce();
  });
});
