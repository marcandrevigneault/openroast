/**
 * Roast alarms — data model and pure functions.
 *
 * Alarms monitor sensor values and trigger audio/visual alerts when
 * thresholds are crossed. Uses the same crossing-detection pattern
 * as the scheduler.
 */

// ──────────────────────────────────────────────
// Sensor source
// ──────────────────────────────────────────────

export type AlarmSensor =
  | { type: "et" }
  | { type: "bt" }
  | { type: "et_ror" }
  | { type: "bt_ror" }
  | { type: "extra"; channelName: string };

export type AlarmDirection = "rising" | "falling" | "both";

export type AlarmSound = "beep" | "chime" | "buzz" | "siren";

export type AlarmRepeat = "once" | "3x";

// ──────────────────────────────────────────────
// Alarm definition & set
// ──────────────────────────────────────────────

export interface AlarmDef {
  id: string;
  sensor: AlarmSensor;
  threshold: number;
  direction: AlarmDirection;
  sound: AlarmSound;
  repeat: AlarmRepeat;
  enabled: boolean;
  fired: boolean;
  playbackId: string | null;
}

export type AlarmStatus = "idle" | "armed" | "completed";

export interface AlarmSet {
  alarms: AlarmDef[];
  status: AlarmStatus;
}

// ──────────────────────────────────────────────
// Evaluation result
// ──────────────────────────────────────────────

export interface AlarmTriggerResult {
  alarmId: string;
  sound: AlarmSound;
  repeat: AlarmRepeat;
  sensorLabel: string;
  threshold: number;
  direction: AlarmDirection;
}

// ──────────────────────────────────────────────
// Pure functions
// ──────────────────────────────────────────────

let nextId = 0;

function generateId(): string {
  return `alarm-${Date.now()}-${nextId++}`;
}

export function createAlarmSet(): AlarmSet {
  return { alarms: [], status: "idle" };
}

export function addAlarm(
  set: AlarmSet,
  config: Omit<AlarmDef, "id" | "fired" | "playbackId">,
): AlarmSet {
  const alarm: AlarmDef = {
    ...config,
    id: generateId(),
    fired: false,
    playbackId: null,
  };
  return { ...set, alarms: [...set.alarms, alarm] };
}

export function removeAlarm(set: AlarmSet, alarmId: string): AlarmSet {
  return { ...set, alarms: set.alarms.filter((a) => a.id !== alarmId) };
}

export function toggleAlarm(set: AlarmSet, alarmId: string): AlarmSet {
  return {
    ...set,
    alarms: set.alarms.map((a) =>
      a.id === alarmId ? { ...a, enabled: !a.enabled } : a,
    ),
  };
}

export function resetAlarms(set: AlarmSet): AlarmSet {
  return {
    ...set,
    status: "idle",
    alarms: set.alarms.map((a) => ({
      ...a,
      fired: false,
      playbackId: null,
    })),
  };
}

// ──────────────────────────────────────────────
// Sensor value resolution
// ──────────────────────────────────────────────

export function resolveSensorValues(
  sensor: AlarmSensor,
  currentEt: number,
  currentBt: number,
  currentEtRor: number,
  currentBtRor: number,
  currentExtras: Record<string, number>,
  previousEt: number,
  previousBt: number,
  previousEtRor: number,
  previousBtRor: number,
  previousExtras: Record<string, number>,
): { current: number; previous: number } | null {
  switch (sensor.type) {
    case "et":
      return { current: currentEt, previous: previousEt };
    case "bt":
      return { current: currentBt, previous: previousBt };
    case "et_ror":
      return { current: currentEtRor, previous: previousEtRor };
    case "bt_ror":
      return { current: currentBtRor, previous: previousBtRor };
    case "extra": {
      const current = currentExtras[sensor.channelName];
      const previous = previousExtras[sensor.channelName];
      if (current === undefined) return null;
      return { current, previous: previous ?? current };
    }
  }
}

// ──────────────────────────────────────────────
// Evaluation
// ──────────────────────────────────────────────

function checkCrossing(
  previous: number,
  current: number,
  threshold: number,
  direction: AlarmDirection,
): boolean {
  const rising = previous < threshold && current >= threshold;
  const falling = previous > threshold && current <= threshold;
  switch (direction) {
    case "rising":
      return rising;
    case "falling":
      return falling;
    case "both":
      return rising || falling;
  }
}

export function evaluateAlarms(
  set: AlarmSet,
  currentEt: number,
  currentBt: number,
  currentEtRor: number,
  currentBtRor: number,
  currentExtras: Record<string, number>,
  previousEt: number,
  previousBt: number,
  previousEtRor: number,
  previousBtRor: number,
  previousExtras: Record<string, number>,
): { set: AlarmSet; triggered: AlarmTriggerResult[] } {
  if (set.status !== "armed") {
    return { set, triggered: [] };
  }

  const triggered: AlarmTriggerResult[] = [];
  const updatedAlarms = set.alarms.map((alarm) => {
    if (alarm.fired || !alarm.enabled) return alarm;

    const values = resolveSensorValues(
      alarm.sensor,
      currentEt,
      currentBt,
      currentEtRor,
      currentBtRor,
      currentExtras,
      previousEt,
      previousBt,
      previousEtRor,
      previousBtRor,
      previousExtras,
    );
    if (!values) return alarm;

    if (
      checkCrossing(
        values.previous,
        values.current,
        alarm.threshold,
        alarm.direction,
      )
    ) {
      triggered.push({
        alarmId: alarm.id,
        sound: alarm.sound,
        repeat: alarm.repeat,
        sensorLabel: formatSensor(alarm.sensor),
        threshold: alarm.threshold,
        direction: alarm.direction,
      });
      return { ...alarm, fired: true };
    }
    return alarm;
  });

  const allDone = updatedAlarms.filter((a) => a.enabled).every((a) => a.fired);

  return {
    set: {
      ...set,
      alarms: updatedAlarms,
      status: allDone ? "completed" : "armed",
    },
    triggered,
  };
}

// ──────────────────────────────────────────────
// Display helpers
// ──────────────────────────────────────────────

export function formatSensor(sensor: AlarmSensor): string {
  switch (sensor.type) {
    case "et":
      return "ET";
    case "bt":
      return "BT";
    case "et_ror":
      return "ET RoR";
    case "bt_ror":
      return "BT RoR";
    case "extra":
      return sensor.channelName;
  }
}

export function formatAlarm(alarm: AlarmDef): string {
  const sensor = formatSensor(alarm.sensor);
  const op =
    alarm.direction === "rising"
      ? ">="
      : alarm.direction === "falling"
        ? "<="
        : "↕";
  return `${sensor} ${op} ${alarm.threshold}`;
}
