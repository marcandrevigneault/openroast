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

export interface MachineState {
  machineId: string;
  machineName: string;
  sessionState: SessionState;
  driverState: DriverState;
  currentTemp: TemperaturePoint | null;
  history: TemperaturePoint[];
  events: RoastEvent[];
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
    case "state":
      return {
        ...state,
        sessionState: msg.state,
        // Clear history when starting a new recording
        history: msg.state === "recording" ? [] : state.history,
        events: msg.state === "recording" ? [] : state.events,
      };
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
    case "alarm":
    case "replay":
    case "control_ack":
      return state;
  }
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
