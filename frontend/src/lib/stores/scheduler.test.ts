import { describe, it, expect } from "vitest";
import {
  createSchedule,
  addStep,
  removeStep,
  updateStep,
  toggleStep,
  reorderStep,
  resetSchedule,
  importFromProfile,
  evaluateSchedule,
  formatTrigger,
  sortSteps,
  type RoastSchedule,
  type ScheduleStep,
  type ControlAction,
} from "./scheduler";
import type { ControlConfig } from "./machine";

const TEST_CONFIGS: ControlConfig[] = [
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

function makeStep(
  overrides: Partial<ScheduleStep> = {},
): Omit<ScheduleStep, "id" | "fired"> {
  return {
    trigger: { type: "time", timestamp_ms: 0 },
    actions: [{ channel: "burner", value: 50 }],
    enabled: true,
    ...overrides,
  };
}

function makeRunningSchedule(steps: ScheduleStep[]): RoastSchedule {
  return { steps, status: "running", sourceProfileName: null };
}

describe("createSchedule", () => {
  it("returns empty idle schedule", () => {
    const s = createSchedule();
    expect(s.steps).toEqual([]);
    expect(s.status).toBe("idle");
    expect(s.sourceProfileName).toBeNull();
  });
});

describe("addStep", () => {
  it("adds step with generated id and fired=false", () => {
    let s = createSchedule();
    s = addStep(s, makeStep());
    expect(s.steps).toHaveLength(1);
    expect(s.steps[0].id).toBeTruthy();
    expect(s.steps[0].fired).toBe(false);
    expect(s.steps[0].enabled).toBe(true);
  });

  it("generates unique ids", () => {
    let s = createSchedule();
    s = addStep(s, makeStep());
    s = addStep(s, makeStep());
    expect(s.steps[0].id).not.toBe(s.steps[1].id);
  });
});

describe("removeStep", () => {
  it("removes step by id", () => {
    let s = createSchedule();
    s = addStep(s, makeStep());
    s = addStep(s, makeStep());
    const idToRemove = s.steps[0].id;
    s = removeStep(s, idToRemove);
    expect(s.steps).toHaveLength(1);
    expect(s.steps[0].id).not.toBe(idToRemove);
  });

  it("returns unchanged schedule for unknown id", () => {
    let s = createSchedule();
    s = addStep(s, makeStep());
    const result = removeStep(s, "nonexistent");
    expect(result.steps).toHaveLength(1);
  });
});

describe("updateStep", () => {
  it("updates step fields", () => {
    let s = createSchedule();
    s = addStep(s, makeStep());
    const id = s.steps[0].id;
    s = updateStep(s, id, {
      trigger: { type: "time", timestamp_ms: 5000 },
    });
    expect(s.steps[0].trigger).toEqual({ type: "time", timestamp_ms: 5000 });
  });

  it("does not affect other steps", () => {
    let s = createSchedule();
    s = addStep(s, makeStep());
    s = addStep(s, makeStep({ trigger: { type: "time", timestamp_ms: 1000 } }));
    s = updateStep(s, s.steps[0].id, { enabled: false });
    expect(s.steps[0].enabled).toBe(false);
    expect(s.steps[1].enabled).toBe(true);
  });
});

describe("toggleStep", () => {
  it("flips enabled flag", () => {
    let s = createSchedule();
    s = addStep(s, makeStep());
    const id = s.steps[0].id;
    expect(s.steps[0].enabled).toBe(true);
    s = toggleStep(s, id);
    expect(s.steps[0].enabled).toBe(false);
    s = toggleStep(s, id);
    expect(s.steps[0].enabled).toBe(true);
  });
});

describe("reorderStep", () => {
  it("moves step up", () => {
    let s = createSchedule();
    s = addStep(s, makeStep({ trigger: { type: "time", timestamp_ms: 0 } }));
    s = addStep(s, makeStep({ trigger: { type: "time", timestamp_ms: 1000 } }));
    const secondId = s.steps[1].id;
    s = reorderStep(s, secondId, "up");
    expect(s.steps[0].id).toBe(secondId);
  });

  it("moves step down", () => {
    let s = createSchedule();
    s = addStep(s, makeStep({ trigger: { type: "time", timestamp_ms: 0 } }));
    s = addStep(s, makeStep({ trigger: { type: "time", timestamp_ms: 1000 } }));
    const firstId = s.steps[0].id;
    s = reorderStep(s, firstId, "down");
    expect(s.steps[1].id).toBe(firstId);
  });

  it("does nothing when already at boundary", () => {
    let s = createSchedule();
    s = addStep(s, makeStep());
    const id = s.steps[0].id;
    const before = s.steps.map((st) => st.id);
    s = reorderStep(s, id, "up");
    expect(s.steps.map((st) => st.id)).toEqual(before);
  });
});

describe("resetSchedule", () => {
  it("clears fired flags and sets status to idle", () => {
    const steps: ScheduleStep[] = [
      {
        id: "a",
        trigger: { type: "time", timestamp_ms: 0 },
        actions: [{ channel: "burner", value: 50 }],
        fired: true,
        enabled: true,
      },
      {
        id: "b",
        trigger: { type: "time", timestamp_ms: 1000 },
        actions: [{ channel: "burner", value: 80 }],
        fired: true,
        enabled: true,
      },
    ];
    const s: RoastSchedule = {
      steps,
      status: "completed",
      sourceProfileName: null,
    };
    const result = resetSchedule(s);
    expect(result.status).toBe("idle");
    expect(result.steps.every((st) => !st.fired)).toBe(true);
  });
});

describe("importFromProfile", () => {
  it("converts profile controls to time-triggered steps", () => {
    const controls: Record<string, [number, number][]> = {
      Burner: [
        [0, 50],
        [3000, 80],
      ],
      Airflow: [[0, 30]],
    };
    const steps = importFromProfile(controls, TEST_CONFIGS);
    expect(steps).toHaveLength(2);
    // t=0 has both burner and airflow
    expect(steps[0].trigger).toEqual({ type: "time", timestamp_ms: 0 });
    expect(steps[0].actions).toHaveLength(2);
    // t=3000 has only burner
    expect(steps[1].trigger).toEqual({ type: "time", timestamp_ms: 3000 });
    expect(steps[1].actions).toHaveLength(1);
    expect(steps[1].actions[0]).toEqual({ channel: "burner", value: 80 });
  });

  it("skips unknown channel names", () => {
    const controls: Record<string, [number, number][]> = {
      Unknown: [[0, 50]],
    };
    const steps = importFromProfile(controls, TEST_CONFIGS);
    expect(steps).toHaveLength(0);
  });

  it("returns empty for empty controls", () => {
    const steps = importFromProfile({}, TEST_CONFIGS);
    expect(steps).toHaveLength(0);
  });

  it("sorts by timestamp", () => {
    const controls: Record<string, [number, number][]> = {
      Burner: [
        [5000, 80],
        [1000, 50],
      ],
    };
    const steps = importFromProfile(controls, TEST_CONFIGS);
    expect(steps[0].trigger).toEqual({ type: "time", timestamp_ms: 1000 });
    expect(steps[1].trigger).toEqual({ type: "time", timestamp_ms: 5000 });
  });

  it("maps channel names to channel IDs", () => {
    const controls: Record<string, [number, number][]> = {
      Burner: [[0, 50]],
    };
    const steps = importFromProfile(controls, TEST_CONFIGS);
    expect(steps[0].actions[0].channel).toBe("burner");
  });
});

describe("evaluateSchedule", () => {
  it("does nothing when status is idle", () => {
    const s: RoastSchedule = {
      steps: [
        {
          id: "a",
          trigger: { type: "time", timestamp_ms: 0 },
          actions: [{ channel: "burner", value: 50 }],
          fired: false,
          enabled: true,
        },
      ],
      status: "idle",
      sourceProfileName: null,
    };
    const result = evaluateSchedule(s, 1000, 200, 250, 199, 249);
    expect(result.firedActions).toHaveLength(0);
    expect(result.schedule.steps[0].fired).toBe(false);
  });

  it("does nothing when status is paused", () => {
    const s: RoastSchedule = {
      steps: [
        {
          id: "a",
          trigger: { type: "time", timestamp_ms: 0 },
          actions: [{ channel: "burner", value: 50 }],
          fired: false,
          enabled: true,
        },
      ],
      status: "paused",
      sourceProfileName: null,
    };
    const result = evaluateSchedule(s, 1000, 200, 250, 199, 249);
    expect(result.firedActions).toHaveLength(0);
  });

  it("fires time trigger when elapsed >= threshold", () => {
    const s = makeRunningSchedule([
      {
        id: "a",
        trigger: { type: "time", timestamp_ms: 5000 },
        actions: [{ channel: "burner", value: 80 }],
        fired: false,
        enabled: true,
      },
    ]);
    const result = evaluateSchedule(s, 5000, 200, 250, 199, 249);
    expect(result.firedActions).toEqual([{ channel: "burner", value: 80 }]);
    expect(result.schedule.steps[0].fired).toBe(true);
  });

  it("does not fire time trigger before threshold", () => {
    const s = makeRunningSchedule([
      {
        id: "a",
        trigger: { type: "time", timestamp_ms: 5000 },
        actions: [{ channel: "burner", value: 80 }],
        fired: false,
        enabled: true,
      },
    ]);
    const result = evaluateSchedule(s, 4999, 200, 250, 199, 249);
    expect(result.firedActions).toHaveLength(0);
    expect(result.schedule.steps[0].fired).toBe(false);
  });

  it("fires BT threshold on rising crossing", () => {
    const s = makeRunningSchedule([
      {
        id: "a",
        trigger: {
          type: "bt_threshold",
          temperature: 150,
          direction: "rising",
        },
        actions: [{ channel: "airflow", value: 60 }],
        fired: false,
        enabled: true,
      },
    ]);
    const result = evaluateSchedule(s, 3000, 151, 250, 149, 249);
    expect(result.firedActions).toEqual([{ channel: "airflow", value: 60 }]);
  });

  it("does not fire BT rising when already above", () => {
    const s = makeRunningSchedule([
      {
        id: "a",
        trigger: {
          type: "bt_threshold",
          temperature: 150,
          direction: "rising",
        },
        actions: [{ channel: "airflow", value: 60 }],
        fired: false,
        enabled: true,
      },
    ]);
    const result = evaluateSchedule(s, 3000, 160, 250, 155, 249);
    expect(result.firedActions).toHaveLength(0);
  });

  it("fires BT threshold on falling crossing", () => {
    const s = makeRunningSchedule([
      {
        id: "a",
        trigger: {
          type: "bt_threshold",
          temperature: 150,
          direction: "falling",
        },
        actions: [{ channel: "burner", value: 0 }],
        fired: false,
        enabled: true,
      },
    ]);
    const result = evaluateSchedule(s, 3000, 149, 250, 151, 249);
    expect(result.firedActions).toEqual([{ channel: "burner", value: 0 }]);
  });

  it("fires ET threshold on rising crossing", () => {
    const s = makeRunningSchedule([
      {
        id: "a",
        trigger: {
          type: "et_threshold",
          temperature: 200,
          direction: "rising",
        },
        actions: [{ channel: "burner", value: 70 }],
        fired: false,
        enabled: true,
      },
    ]);
    const result = evaluateSchedule(s, 3000, 160, 201, 155, 199);
    expect(result.firedActions).toEqual([{ channel: "burner", value: 70 }]);
  });

  it("skips already-fired steps", () => {
    const s = makeRunningSchedule([
      {
        id: "a",
        trigger: { type: "time", timestamp_ms: 0 },
        actions: [{ channel: "burner", value: 50 }],
        fired: true,
        enabled: true,
      },
    ]);
    const result = evaluateSchedule(s, 1000, 200, 250, 199, 249);
    expect(result.firedActions).toHaveLength(0);
  });

  it("skips disabled steps", () => {
    const s = makeRunningSchedule([
      {
        id: "a",
        trigger: { type: "time", timestamp_ms: 0 },
        actions: [{ channel: "burner", value: 50 }],
        fired: false,
        enabled: false,
      },
    ]);
    const result = evaluateSchedule(s, 1000, 200, 250, 199, 249);
    expect(result.firedActions).toHaveLength(0);
  });

  it("fires multiple steps in one evaluation", () => {
    const s = makeRunningSchedule([
      {
        id: "a",
        trigger: { type: "time", timestamp_ms: 0 },
        actions: [{ channel: "burner", value: 50 }],
        fired: false,
        enabled: true,
      },
      {
        id: "b",
        trigger: { type: "time", timestamp_ms: 1000 },
        actions: [{ channel: "airflow", value: 30 }],
        fired: false,
        enabled: true,
      },
    ]);
    const result = evaluateSchedule(s, 2000, 200, 250, 199, 249);
    expect(result.firedActions).toHaveLength(2);
    expect(result.schedule.steps[0].fired).toBe(true);
    expect(result.schedule.steps[1].fired).toBe(true);
  });

  it("returns completed when all enabled steps are fired", () => {
    const s = makeRunningSchedule([
      {
        id: "a",
        trigger: { type: "time", timestamp_ms: 0 },
        actions: [{ channel: "burner", value: 50 }],
        fired: false,
        enabled: true,
      },
      {
        id: "b",
        trigger: { type: "time", timestamp_ms: 1000 },
        actions: [{ channel: "airflow", value: 30 }],
        fired: false,
        enabled: false,
      },
    ]);
    const result = evaluateSchedule(s, 1000, 200, 250, 199, 249);
    expect(result.schedule.status).toBe("completed");
  });

  it("stays running when unfired enabled steps remain", () => {
    const s = makeRunningSchedule([
      {
        id: "a",
        trigger: { type: "time", timestamp_ms: 0 },
        actions: [{ channel: "burner", value: 50 }],
        fired: false,
        enabled: true,
      },
      {
        id: "b",
        trigger: { type: "time", timestamp_ms: 10000 },
        actions: [{ channel: "airflow", value: 30 }],
        fired: false,
        enabled: true,
      },
    ]);
    const result = evaluateSchedule(s, 1000, 200, 250, 199, 249);
    expect(result.schedule.status).toBe("running");
  });
});

describe("formatTrigger", () => {
  it("formats time trigger", () => {
    expect(formatTrigger({ type: "time", timestamp_ms: 90000 })).toBe(
      "at 1:30",
    );
  });

  it("formats BT rising threshold", () => {
    expect(
      formatTrigger({
        type: "bt_threshold",
        temperature: 150,
        direction: "rising",
      }),
    ).toBe("BT >= 150°C");
  });

  it("formats BT falling threshold", () => {
    expect(
      formatTrigger({
        type: "bt_threshold",
        temperature: 150,
        direction: "falling",
      }),
    ).toBe("BT <= 150°C");
  });

  it("formats ET rising threshold", () => {
    expect(
      formatTrigger({
        type: "et_threshold",
        temperature: 200,
        direction: "rising",
      }),
    ).toBe("ET >= 200°C");
  });
});

describe("sortSteps", () => {
  it("sorts time triggers ascending", () => {
    const steps: ScheduleStep[] = [
      {
        id: "b",
        trigger: { type: "time", timestamp_ms: 5000 },
        actions: [],
        fired: false,
        enabled: true,
      },
      {
        id: "a",
        trigger: { type: "time", timestamp_ms: 1000 },
        actions: [],
        fired: false,
        enabled: true,
      },
    ];
    const sorted = sortSteps(steps);
    expect(sorted[0].id).toBe("a");
    expect(sorted[1].id).toBe("b");
  });

  it("puts time triggers before BT before ET", () => {
    const steps: ScheduleStep[] = [
      {
        id: "et",
        trigger: {
          type: "et_threshold",
          temperature: 200,
          direction: "rising",
        },
        actions: [],
        fired: false,
        enabled: true,
      },
      {
        id: "time",
        trigger: { type: "time", timestamp_ms: 0 },
        actions: [],
        fired: false,
        enabled: true,
      },
      {
        id: "bt",
        trigger: {
          type: "bt_threshold",
          temperature: 150,
          direction: "rising",
        },
        actions: [],
        fired: false,
        enabled: true,
      },
    ];
    const sorted = sortSteps(steps);
    expect(sorted.map((s) => s.id)).toEqual(["time", "bt", "et"]);
  });

  it("sorts BT thresholds ascending by temperature", () => {
    const steps: ScheduleStep[] = [
      {
        id: "b",
        trigger: {
          type: "bt_threshold",
          temperature: 200,
          direction: "rising",
        },
        actions: [],
        fired: false,
        enabled: true,
      },
      {
        id: "a",
        trigger: {
          type: "bt_threshold",
          temperature: 150,
          direction: "rising",
        },
        actions: [],
        fired: false,
        enabled: true,
      },
    ];
    const sorted = sortSteps(steps);
    expect(sorted[0].id).toBe("a");
  });
});
