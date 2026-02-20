import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/svelte";
import SchedulerDialog from "./SchedulerDialog.svelte";
import {
  createSchedule,
  type RoastSchedule,
  type ScheduleStep,
} from "$lib/stores/scheduler";
import type { MachineState } from "$lib/stores/machine";
import { createInitialState } from "$lib/stores/machine";

const TEST_CONTROLS = [
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

function makeMachine(): MachineState {
  return {
    ...createInitialState("m1", "Test Machine", TEST_CONTROLS, []),
    driverState: "connected",
    sessionState: "monitoring",
  };
}

function makeSteps(): ScheduleStep[] {
  return [
    {
      id: "s1",
      trigger: { type: "time", timestamp_ms: 0 },
      actions: [{ channel: "burner", value: 50 }],
      fired: false,
      enabled: true,
    },
    {
      id: "s2",
      trigger: { type: "time", timestamp_ms: 60000 },
      actions: [{ channel: "airflow", value: 70 }],
      fired: false,
      enabled: true,
    },
  ];
}

describe("SchedulerDialog", () => {
  it("does not render when open is false", () => {
    render(SchedulerDialog, {
      props: {
        open: false,
        machine: makeMachine(),
        schedule: createSchedule(),
        onclose: vi.fn(),
        onschedulechange: vi.fn(),
      },
    });
    expect(screen.queryByText("Roast Schedule")).not.toBeInTheDocument();
  });

  it("renders when open is true", () => {
    render(SchedulerDialog, {
      props: {
        open: true,
        machine: makeMachine(),
        schedule: createSchedule(),
        onclose: vi.fn(),
        onschedulechange: vi.fn(),
      },
    });
    expect(screen.getByText("Roast Schedule")).toBeInTheDocument();
  });

  it("shows empty state when no steps", () => {
    render(SchedulerDialog, {
      props: {
        open: true,
        machine: makeMachine(),
        schedule: createSchedule(),
        onclose: vi.fn(),
        onschedulechange: vi.fn(),
      },
    });
    expect(screen.getByText(/No steps yet/)).toBeInTheDocument();
  });

  it("shows steps with trigger and action text", () => {
    const schedule: RoastSchedule = {
      steps: makeSteps(),
      status: "idle",
      sourceProfileName: null,
    };
    render(SchedulerDialog, {
      props: {
        open: true,
        machine: makeMachine(),
        schedule,
        onclose: vi.fn(),
        onschedulechange: vi.fn(),
      },
    });
    expect(screen.getByText("at 0:00")).toBeInTheDocument();
    expect(screen.getByText("at 1:00")).toBeInTheDocument();
    expect(screen.getByText("Burner: 50%")).toBeInTheDocument();
    expect(screen.getByText("Airflow: 70%")).toBeInTheDocument();
  });

  it("calls onclose when close button clicked", async () => {
    const onclose = vi.fn();
    render(SchedulerDialog, {
      props: {
        open: true,
        machine: makeMachine(),
        schedule: createSchedule(),
        onclose,
        onschedulechange: vi.fn(),
      },
    });
    await fireEvent.click(screen.getByLabelText("Close"));
    expect(onclose).toHaveBeenCalledOnce();
  });

  it("calls onschedulechange when step is removed", async () => {
    const onschedulechange = vi.fn();
    const schedule: RoastSchedule = {
      steps: makeSteps(),
      status: "idle",
      sourceProfileName: null,
    };
    render(SchedulerDialog, {
      props: {
        open: true,
        machine: makeMachine(),
        schedule,
        onclose: vi.fn(),
        onschedulechange,
      },
    });
    const removeButtons = screen.getAllByTitle("Remove step");
    await fireEvent.click(removeButtons[0]);
    expect(onschedulechange).toHaveBeenCalledOnce();
    const updated = onschedulechange.mock.calls[0][0] as RoastSchedule;
    expect(updated.steps).toHaveLength(1);
  });

  it("shows Start Schedule button when idle with steps", () => {
    const schedule: RoastSchedule = {
      steps: makeSteps(),
      status: "idle",
      sourceProfileName: null,
    };
    render(SchedulerDialog, {
      props: {
        open: true,
        machine: makeMachine(),
        schedule,
        onclose: vi.fn(),
        onschedulechange: vi.fn(),
      },
    });
    expect(screen.getByText("Start Schedule")).toBeInTheDocument();
  });

  it("shows Pause and Stop when running", () => {
    const schedule: RoastSchedule = {
      steps: makeSteps(),
      status: "running",
      sourceProfileName: null,
    };
    render(SchedulerDialog, {
      props: {
        open: true,
        machine: makeMachine(),
        schedule,
        onclose: vi.fn(),
        onschedulechange: vi.fn(),
      },
    });
    expect(screen.getByText("Pause")).toBeInTheDocument();
    expect(screen.getByText("Stop")).toBeInTheDocument();
  });

  it("shows source profile name", () => {
    const schedule: RoastSchedule = {
      steps: makeSteps(),
      status: "idle",
      sourceProfileName: "Ethiopian Light",
    };
    render(SchedulerDialog, {
      props: {
        open: true,
        machine: makeMachine(),
        schedule,
        onclose: vi.fn(),
        onschedulechange: vi.fn(),
      },
    });
    expect(screen.getByText("from: Ethiopian Light")).toBeInTheDocument();
  });

  it("shows step count badge", () => {
    const schedule: RoastSchedule = {
      steps: makeSteps(),
      status: "idle",
      sourceProfileName: null,
    };
    render(SchedulerDialog, {
      props: {
        open: true,
        machine: makeMachine(),
        schedule,
        onclose: vi.fn(),
        onschedulechange: vi.fn(),
      },
    });
    expect(screen.getByText("(0/2)")).toBeInTheDocument();
  });

  it("shows fired checkmarks on completed steps", () => {
    const steps = makeSteps();
    steps[0].fired = true;
    const schedule: RoastSchedule = {
      steps,
      status: "running",
      sourceProfileName: null,
    };
    const { container } = render(SchedulerDialog, {
      props: {
        open: true,
        machine: makeMachine(),
        schedule,
        onclose: vi.fn(),
        onschedulechange: vi.fn(),
      },
    });
    const checks = container.querySelectorAll(".step-check");
    expect(checks).toHaveLength(1);
  });

  it("shows + Add button and opens form on click", async () => {
    render(SchedulerDialog, {
      props: {
        open: true,
        machine: makeMachine(),
        schedule: createSchedule(),
        onclose: vi.fn(),
        onschedulechange: vi.fn(),
      },
    });
    const addBtn = screen.getByText("+ Add");
    await fireEvent.click(addBtn);
    expect(screen.getByText("Add Step")).toBeInTheDocument();
  });

  it("shows Clear All button when steps exist", () => {
    const schedule: RoastSchedule = {
      steps: makeSteps(),
      status: "idle",
      sourceProfileName: null,
    };
    render(SchedulerDialog, {
      props: {
        open: true,
        machine: makeMachine(),
        schedule,
        onclose: vi.fn(),
        onschedulechange: vi.fn(),
      },
    });
    expect(screen.getByText("Clear All")).toBeInTheDocument();
  });

  it("calls onschedulechange with empty schedule on Clear All", async () => {
    const onschedulechange = vi.fn();
    const schedule: RoastSchedule = {
      steps: makeSteps(),
      status: "idle",
      sourceProfileName: null,
    };
    render(SchedulerDialog, {
      props: {
        open: true,
        machine: makeMachine(),
        schedule,
        onclose: vi.fn(),
        onschedulechange,
      },
    });
    await fireEvent.click(screen.getByText("Clear All"));
    expect(onschedulechange).toHaveBeenCalledOnce();
    const updated = onschedulechange.mock.calls[0][0] as RoastSchedule;
    expect(updated.steps).toHaveLength(0);
  });
});
