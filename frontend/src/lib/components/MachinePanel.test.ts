import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/svelte";
import MachinePanel from "./MachinePanel.svelte";
import {
  createInitialState,
  type MachineState,
  type ControlConfig,
} from "$lib/stores/machine";
import { getToasts, clearToasts } from "$lib/stores/toast";

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
  beforeEach(() => {
    vi.useFakeTimers();
    clearToasts();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

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

  it("shows control sliders always visible", () => {
    const { container } = render(MachinePanel, {
      props: { machine: makeMachine() },
    });
    const sliders = container.querySelectorAll('input[type="range"]');
    expect(sliders).toHaveLength(3);
  });

  it("shows slider labels", () => {
    render(MachinePanel, { props: { machine: makeMachine() } });
    // Labels appear on both sliders and control chart legend
    expect(screen.getAllByText("Burner").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Airflow").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Drum").length).toBeGreaterThanOrEqual(1);
  });

  it("hides controls section when no controls configured", () => {
    const machine = makeMachine({ controls: [] });
    const { container } = render(MachinePanel, { props: { machine } });
    const sliders = container.querySelectorAll('input[type="range"]');
    expect(sliders).toHaveLength(0);
  });

  it("renders event buttons", () => {
    render(MachinePanel, {
      props: { machine: makeMachine({ sessionState: "recording" }) },
    });
    expect(screen.getByText("CHARGE")).toBeInTheDocument();
    expect(screen.getByText("DROP")).toBeInTheDocument();
  });

  it("dispatches error as toast notification", async () => {
    render(MachinePanel, {
      props: { machine: makeMachine({ error: "Connection lost" }) },
    });
    await vi.advanceTimersByTimeAsync(0);
    const toasts = getToasts();
    expect(toasts).toHaveLength(1);
    expect(toasts[0].message).toBe("Connection lost");
    expect(toasts[0].machineLabel).toBe("Test Roaster");
    expect(toasts[0].type).toBe("error");
  });

  it("does not show inline error banner", () => {
    const { container } = render(MachinePanel, {
      props: { machine: makeMachine({ error: "Connection lost" }) },
    });
    expect(container.querySelector(".error-banner")).toBeNull();
  });

  it("renders chart", () => {
    const { container } = render(MachinePanel, {
      props: { machine: makeMachine() },
    });
    expect(container.querySelector("svg")).toBeTruthy();
  });

  it("enables sliders when connected", () => {
    const { container } = render(MachinePanel, {
      props: {
        machine: makeMachine({
          sessionState: "idle",
          driverState: "connected",
        }),
      },
    });
    const sliders = container.querySelectorAll('input[type="range"]');
    sliders.forEach((slider) => {
      expect(slider).not.toBeDisabled();
    });
  });

  it("disables sliders when disconnected", () => {
    const { container } = render(MachinePanel, {
      props: { machine: makeMachine({ driverState: "disconnected" }) },
    });
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

  it("shows settings gear button", () => {
    render(MachinePanel, { props: { machine: makeMachine() } });
    expect(screen.getByTitle("Machine settings")).toBeInTheDocument();
  });

  it("shows retry button in header when disconnected", () => {
    render(MachinePanel, {
      props: {
        machine: makeMachine({ driverState: "disconnected" }),
        onretry: () => {},
      },
    });
    expect(screen.getByTitle("Retry connection")).toBeInTheDocument();
  });

  it("hides retry button when connected", () => {
    render(MachinePanel, {
      props: {
        machine: makeMachine({ driverState: "connected" }),
        onretry: () => {},
      },
    });
    expect(screen.queryByTitle("Retry connection")).not.toBeInTheDocument();
  });

  it("shows reset button when onreset provided", () => {
    render(MachinePanel, {
      props: { machine: makeMachine(), onreset: () => {} },
    });
    expect(screen.getByTitle("Reset chart")).toBeInTheDocument();
  });

  it("hides reset button when onreset not provided", () => {
    render(MachinePanel, {
      props: { machine: makeMachine() },
    });
    expect(screen.queryByTitle("Reset chart")).not.toBeInTheDocument();
  });

  it("event buttons are always disabled", () => {
    const { container } = render(MachinePanel, {
      props: { machine: makeMachine({ sessionState: "recording" }) },
    });
    const eventBtns = container.querySelectorAll(".event-btn");
    eventBtns.forEach((btn) => {
      expect(btn).toBeDisabled();
    });
  });
});
