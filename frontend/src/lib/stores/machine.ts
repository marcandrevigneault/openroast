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
  burner: number;
  airflow: number;
  drum: number;
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
  error: string | null;
}

export function createInitialState(
  machineId: string,
  machineName: string,
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
      return {
        ...state,
        currentTemp: point,
        history: [...state.history, point],
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
      const isNewRecording = msg.state === "recording";
      return {
        ...state,
        sessionState: msg.state,
        // Clear history when starting a new recording
        history: isNewRecording ? [] : state.history,
        events: isNewRecording ? [] : state.events,
        controlHistory: isNewRecording ? [] : state.controlHistory,
      };
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
    case "control_ack": {
      const controls = state.currentControls ?? {
        timestamp_ms: 0,
        burner: 0,
        airflow: 0,
        drum: 0,
      };
      return {
        ...state,
        currentControls: {
          ...controls,
          timestamp_ms: state.currentTemp?.timestamp_ms ?? 0,
          [msg.channel]: msg.value,
        },
      };
    }
    case "alarm":
    case "replay":
      return state;
  }
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
  const base = state.currentControls ?? {
    timestamp_ms: 0,
    burner: 0,
    airflow: 0,
    drum: 0,
  };
  const point: ControlPoint = {
    ...base,
    timestamp_ms,
    [channel]: value,
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
