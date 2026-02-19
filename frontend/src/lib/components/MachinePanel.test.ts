import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/svelte";
import MachinePanel from "./MachinePanel.svelte";
import { createInitialState, type MachineState } from "$lib/stores/machine";

function makeMachine(overrides: Partial<MachineState> = {}): MachineState {
  return {
    ...createInitialState("m1", "Test Roaster"),
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

  it("renders temperature displays", () => {
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
    expect(screen.getByText("215.3")).toBeInTheDocument();
    expect(screen.getByText("190.7")).toBeInTheDocument();
  });

  it("renders slider controls", () => {
    render(MachinePanel, { props: { machine: makeMachine() } });
    expect(screen.getByText("Burner")).toBeInTheDocument();
    expect(screen.getByText("Airflow")).toBeInTheDocument();
    expect(screen.getByText("Drum")).toBeInTheDocument();
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
});
