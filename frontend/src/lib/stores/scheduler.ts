/**
 * Roast automation scheduler — data model and pure functions.
 *
 * A schedule is a list of steps, each with a trigger condition and one or more
 * control actions. The scheduler evaluates against live machine state and fires
 * control commands when triggers are met.
 */

import type { ControlConfig } from "./machine";
import { formatTime } from "./machine";

// ──────────────────────────────────────────────
// Trigger types
// ──────────────────────────────────────────────

export interface TimeTrigger {
  type: "time";
  timestamp_ms: number;
}

export interface BtThresholdTrigger {
  type: "bt_threshold";
  temperature: number;
  direction: "rising" | "falling";
}

export interface EtThresholdTrigger {
  type: "et_threshold";
  temperature: number;
  direction: "rising" | "falling";
}

export type ScheduleTrigger =
  | TimeTrigger
  | BtThresholdTrigger
  | EtThresholdTrigger;

// ──────────────────────────────────────────────
// Actions
// ──────────────────────────────────────────────

export interface ControlAction {
  channel: string;
  value: number; // native range (e.g., 0-100)
}

// ──────────────────────────────────────────────
// Step & Schedule
// ──────────────────────────────────────────────

export interface ScheduleStep {
  id: string;
  trigger: ScheduleTrigger;
  actions: ControlAction[];
  fired: boolean;
  enabled: boolean;
}

export type SchedulerStatus = "idle" | "running" | "paused" | "completed";

export interface RoastSchedule {
  steps: ScheduleStep[];
  status: SchedulerStatus;
  sourceProfileName: string | null;
}

// ──────────────────────────────────────────────
// Pure functions
// ──────────────────────────────────────────────

let nextId = 0;

function generateId(): string {
  return `step-${Date.now()}-${nextId++}`;
}

export function createSchedule(): RoastSchedule {
  return { steps: [], status: "idle", sourceProfileName: null };
}

export function addStep(
  schedule: RoastSchedule,
  step: Omit<ScheduleStep, "id" | "fired">,
): RoastSchedule {
  const newStep: ScheduleStep = { ...step, id: generateId(), fired: false };
  return { ...schedule, steps: [...schedule.steps, newStep] };
}

export function removeStep(
  schedule: RoastSchedule,
  stepId: string,
): RoastSchedule {
  return {
    ...schedule,
    steps: schedule.steps.filter((s) => s.id !== stepId),
  };
}

export function updateStep(
  schedule: RoastSchedule,
  stepId: string,
  updates: Partial<Omit<ScheduleStep, "id">>,
): RoastSchedule {
  return {
    ...schedule,
    steps: schedule.steps.map((s) =>
      s.id === stepId ? { ...s, ...updates } : s,
    ),
  };
}

export function toggleStep(
  schedule: RoastSchedule,
  stepId: string,
): RoastSchedule {
  return {
    ...schedule,
    steps: schedule.steps.map((s) =>
      s.id === stepId ? { ...s, enabled: !s.enabled } : s,
    ),
  };
}

export function reorderStep(
  schedule: RoastSchedule,
  stepId: string,
  direction: "up" | "down",
): RoastSchedule {
  const idx = schedule.steps.findIndex((s) => s.id === stepId);
  if (idx === -1) return schedule;
  const targetIdx = direction === "up" ? idx - 1 : idx + 1;
  if (targetIdx < 0 || targetIdx >= schedule.steps.length) return schedule;

  const steps = [...schedule.steps];
  [steps[idx], steps[targetIdx]] = [steps[targetIdx], steps[idx]];
  return { ...schedule, steps };
}

export function resetSchedule(schedule: RoastSchedule): RoastSchedule {
  return {
    ...schedule,
    status: "idle",
    steps: schedule.steps.map((s) => ({ ...s, fired: false })),
  };
}

/**
 * Convert a saved profile's controls into schedule steps.
 *
 * Profile controls are stored as `Record<string, [number, number][]>` where
 * keys are channel *names* (e.g., "Burner") and values are [timestamp_ms, native_value].
 * This function maps names to channel IDs using the machine's ControlConfig[].
 */
export function importFromProfile(
  controls: Record<string, [number, number][]>,
  controlConfigs: ControlConfig[],
): ScheduleStep[] {
  const nameToChannel = new Map<string, string>();
  for (const cfg of controlConfigs) {
    nameToChannel.set(cfg.name, cfg.channel);
  }

  // Group control points by timestamp
  const byTimestamp = new Map<number, ControlAction[]>();
  for (const [channelName, points] of Object.entries(controls)) {
    const channel = nameToChannel.get(channelName);
    if (!channel) continue;
    for (const [timestamp_ms, value] of points) {
      const existing = byTimestamp.get(timestamp_ms) ?? [];
      existing.push({ channel, value });
      byTimestamp.set(timestamp_ms, existing);
    }
  }

  return Array.from(byTimestamp.entries())
    .sort(([a], [b]) => a - b)
    .map(([timestamp_ms, actions], i) => ({
      id: `imported-${i}`,
      trigger: { type: "time" as const, timestamp_ms },
      actions,
      fired: false,
      enabled: true,
    }));
}

/**
 * Evaluate a running schedule against current machine state.
 *
 * Returns the updated schedule and any actions that should be dispatched.
 * Uses crossing detection for temperature thresholds to avoid re-firing.
 */
export function evaluateSchedule(
  schedule: RoastSchedule,
  elapsedMs: number,
  currentBt: number,
  currentEt: number,
  previousBt: number,
  previousEt: number,
): { schedule: RoastSchedule; firedActions: ControlAction[] } {
  if (schedule.status !== "running") {
    return { schedule, firedActions: [] };
  }

  const firedActions: ControlAction[] = [];
  const updatedSteps = schedule.steps.map((step) => {
    if (step.fired || !step.enabled) return step;

    let shouldFire = false;
    switch (step.trigger.type) {
      case "time":
        shouldFire = elapsedMs >= step.trigger.timestamp_ms;
        break;
      case "bt_threshold":
        shouldFire =
          step.trigger.direction === "rising"
            ? previousBt < step.trigger.temperature &&
              currentBt >= step.trigger.temperature
            : previousBt > step.trigger.temperature &&
              currentBt <= step.trigger.temperature;
        break;
      case "et_threshold":
        shouldFire =
          step.trigger.direction === "rising"
            ? previousEt < step.trigger.temperature &&
              currentEt >= step.trigger.temperature
            : previousEt > step.trigger.temperature &&
              currentEt <= step.trigger.temperature;
        break;
    }

    if (shouldFire) {
      firedActions.push(...step.actions);
      return { ...step, fired: true };
    }
    return step;
  });

  const allDone = updatedSteps.filter((s) => s.enabled).every((s) => s.fired);

  return {
    schedule: {
      ...schedule,
      steps: updatedSteps,
      status: allDone ? "completed" : "running",
    },
    firedActions,
  };
}

/** Format a trigger for display. */
export function formatTrigger(trigger: ScheduleTrigger): string {
  switch (trigger.type) {
    case "time":
      return `at ${formatTime(trigger.timestamp_ms)}`;
    case "bt_threshold":
      return `BT ${trigger.direction === "rising" ? ">=" : "<="} ${trigger.temperature}°C`;
    case "et_threshold":
      return `ET ${trigger.direction === "rising" ? ">=" : "<="} ${trigger.temperature}°C`;
  }
}

/** Sort steps: time triggers first (ascending), then BT (ascending), then ET (ascending). */
export function sortSteps(steps: ScheduleStep[]): ScheduleStep[] {
  const typeOrder = { time: 0, bt_threshold: 1, et_threshold: 2 };
  return [...steps].sort((a, b) => {
    const ta = typeOrder[a.trigger.type];
    const tb = typeOrder[b.trigger.type];
    if (ta !== tb) return ta - tb;

    if (a.trigger.type === "time" && b.trigger.type === "time") {
      return a.trigger.timestamp_ms - b.trigger.timestamp_ms;
    }
    if (
      (a.trigger.type === "bt_threshold" &&
        b.trigger.type === "bt_threshold") ||
      (a.trigger.type === "et_threshold" && b.trigger.type === "et_threshold")
    ) {
      return (
        (a.trigger as BtThresholdTrigger | EtThresholdTrigger).temperature -
        (b.trigger as BtThresholdTrigger | EtThresholdTrigger).temperature
      );
    }
    return 0;
  });
}
