/**
 * Machine connection store — manages WebSocket connection and state
 * for a single roasting machine.
 */

import type {
  ServerMessage,
  SessionState,
  DriverState,
  RoastEventType,
} from "$lib/types/ws-messages";

export interface TemperaturePoint {
  timestamp_ms: number;
  et: number;
  bt: number;
  et_ror: number;
  bt_ror: number;
}

export interface RoastEvent {
  event_type: RoastEventType;
  timestamp_ms: number;
  auto_detected: boolean;
  bt_at_event: number;
  et_at_event: number;
}

export interface ControlPoint {
  timestamp_ms: number;
  values: Record<string, number>;
}

export interface ControlConfig {
  name: string;
  channel: string;
  min: number;
  max: number;
  step: number;
  unit: string;
}

export interface ExtraChannelConfig {
  name: string;
}

export interface ExtraChannelPoint {
  timestamp_ms: number;
  values: Record<string, number>;
}

export interface MachineState {
  machineId: string;
  machineName: string;
  sessionState: SessionState;
  driverState: DriverState;
  currentTemp: TemperaturePoint | null;
  history: TemperaturePoint[];
  events: RoastEvent[];
  controlHistory: ControlPoint[];
  currentControls: ControlPoint | null;
  controls: ControlConfig[];
  extraChannels: ExtraChannelConfig[];
  extraChannelHistory: ExtraChannelPoint[];
  currentExtraChannels: Record<string, number>;
  error: string | null;
}

export function createInitialState(
  machineId: string,
  machineName: string,
  controls: ControlConfig[] = [],
  extraChannels: ExtraChannelConfig[] = [],
): MachineState {
  return {
    machineId,
    machineName,
    sessionState: "idle",
    driverState: "disconnected",
    currentTemp: null,
    history: [],
    events: [],
    controlHistory: [],
    currentControls: null,
    controls,
    extraChannels,
    extraChannelHistory: [],
    currentExtraChannels: {},
    error: null,
  };
}

/**
 * Process a server message and return the updated state.
 * Pure function — no side effects, easy to test.
 */
export function processMessage(
  state: MachineState,
  msg: ServerMessage,
): MachineState {
  switch (msg.type) {
    case "temperature": {
      const point: TemperaturePoint = {
        timestamp_ms: msg.timestamp_ms,
        et: msg.et,
        bt: msg.bt,
        et_ror: msg.et_ror,
        bt_ror: msg.bt_ror,
      };
      const extras = msg.extra_channels;
      const hasExtras = Object.keys(extras).length > 0;
      // Only accumulate chart data when monitoring or recording
      const isActive =
        state.sessionState === "monitoring" ||
        state.sessionState === "recording";

      // Detect readback value changes and record as control changes
      let updatedCurrentControls = state.currentControls;
      let updatedControlHistory = state.controlHistory;

      if (hasExtras && state.controls.length > 0) {
        const changedValues: Record<string, number> = {};
        for (const ctrl of state.controls) {
          const newVal = extras[ctrl.name];
          const prevVal = state.currentExtraChannels[ctrl.name];
          if (newVal !== undefined && newVal !== prevVal) {
            changedValues[ctrl.channel] = newVal;
          }
        }
        if (Object.keys(changedValues).length > 0) {
          const prevValues = updatedCurrentControls?.values ?? {};
          const roundedTs = Math.round(msg.timestamp_ms / 1000) * 1000;
          updatedCurrentControls = {
            timestamp_ms: roundedTs,
            values: { ...prevValues, ...changedValues },
          };
          if (isActive && state.sessionState === "recording") {
            updatedControlHistory = [
              ...updatedControlHistory,
              { timestamp_ms: roundedTs, values: changedValues },
            ];
          }
        }
      }

      return {
        ...state,
        currentTemp: point,
        history: isActive ? [...state.history, point] : state.history,
        currentControls: updatedCurrentControls,
        controlHistory: updatedControlHistory,
        currentExtraChannels: hasExtras ? extras : state.currentExtraChannels,
        extraChannelHistory:
          isActive && hasExtras
            ? [
                ...state.extraChannelHistory,
                { timestamp_ms: msg.timestamp_ms, values: extras },
              ]
            : state.extraChannelHistory,
        error: null,
      };
    }
    case "event": {
      const evt: RoastEvent = {
        event_type: msg.event_type,
        timestamp_ms: msg.timestamp_ms,
        auto_detected: msg.auto_detected,
        bt_at_event: msg.bt_at_event,
        et_at_event: msg.et_at_event,
      };
      return {
        ...state,
        events: [...state.events, evt],
      };
    }
    case "state": {
      if (msg.state === "recording") {
        // Keep last 5 seconds of monitoring data, rebased to negative
        // timestamps (e.g. -5000 to 0). The backend resets its clock on
        // START_RECORDING, so fresh data will arrive starting from ~0.
        const TAIL_MS = 5000;
        const lastTs =
          state.history.length > 0
            ? state.history[state.history.length - 1].timestamp_ms
            : 0;
        const cutoff = lastTs - TAIL_MS;
        // Offset so the last monitoring point lands at t=0
        const offset = lastTs;

        // Snapshot control values at t=0 from both readback and slider values
        const snapshotValues: Record<string, number> = {};
        for (const ctrl of state.controls) {
          const readback = state.currentExtraChannels[ctrl.name];
          if (readback !== undefined) {
            snapshotValues[ctrl.channel] = readback;
          }
        }
        if (state.currentControls) {
          Object.assign(snapshotValues, state.currentControls.values);
        }
        const initialControls: ControlPoint[] =
          Object.keys(snapshotValues).length > 0
            ? [{ timestamp_ms: 0, values: snapshotValues }]
            : [];

        return {
          ...state,
          sessionState: msg.state,
          history: state.history
            .filter((p) => p.timestamp_ms >= cutoff)
            .map((p) => ({ ...p, timestamp_ms: p.timestamp_ms - offset })),
          events: [],
          controlHistory: initialControls,
          extraChannelHistory: state.extraChannelHistory
            .filter((p) => p.timestamp_ms >= cutoff)
            .map((p) => ({ ...p, timestamp_ms: p.timestamp_ms - offset })),
        };
      }
      if (msg.state === "monitoring") {
        return {
          ...state,
          sessionState: msg.state,
          currentTemp: null,
          history: [],
          controlHistory: [],
          extraChannelHistory: [],
          events: [],
        };
      }
      return { ...state, sessionState: msg.state };
    }
    case "connection":
      return {
        ...state,
        driverState: msg.driver_state,
      };
    case "error":
      return {
        ...state,
        error: msg.message,
      };
    case "control_ack":
      // No-op — control values tracked via readback (temperature messages)
      // and slider input (processControlInput). The ack carries normalized
      // 0-1 values which would overwrite native values.
      return state;
    case "alarm":
    case "replay":
      return state;
  }
}

/**
 * Record a user-initiated control change with native slider values.
 * Always updates currentControls; appends to controlHistory only during recording.
 * Called directly when the user moves a slider — does not depend on WS round-trip.
 */
export function processControlInput(
  state: MachineState,
  channel: string,
  nativeValue: number,
): MachineState {
  const rawTs = state.currentTemp?.timestamp_ms ?? 0;
  const ts = Math.round(rawTs / 1000) * 1000;
  const prevValues = state.currentControls?.values ?? {};
  const newControls: ControlPoint = {
    timestamp_ms: ts,
    values: { ...prevValues, [channel]: nativeValue },
  };
  const isRecording = state.sessionState === "recording";
  return {
    ...state,
    currentControls: newControls,
    controlHistory: isRecording
      ? [
          ...state.controlHistory,
          { timestamp_ms: ts, values: { [channel]: nativeValue } },
        ]
      : state.controlHistory,
  };
}

/**
 * Record a control change into the machine state.
 * Appends to controlHistory and updates currentControls.
 */
export function recordControlChange(
  state: MachineState,
  channel: string,
  value: number,
  timestamp_ms: number,
): MachineState {
  const prevValues = state.currentControls?.values ?? {};
  const point: ControlPoint = {
    timestamp_ms,
    values: { ...prevValues, [channel]: value },
  };
  return {
    ...state,
    currentControls: point,
    controlHistory: [...state.controlHistory, point],
  };
}

/**
 * Format milliseconds as mm:ss for display.
 */
export function formatTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}
