/**
 * WebSocket message type definitions.
 *
 * These types define the wire contract between frontend and backend.
 * Both sides MUST stay in sync — the Python counterpart is at
 * backend/src/openroast/models/ws_messages.py.
 */

// ──────────────────────────────────────────────
// Shared enums
// ──────────────────────────────────────────────

export type RoastEventType =
  | "CHARGE"
  | "DRY_END"
  | "FCs"
  | "FCe"
  | "SCs"
  | "SCe"
  | "DROP"
  | "COOL"
  | "TP";

export type SessionState = "idle" | "monitoring" | "recording" | "finished";

export type AlarmSeverity = "info" | "warning" | "critical";

export type DriverState = "disconnected" | "connecting" | "connected" | "error";

// ──────────────────────────────────────────────
// Server → Client messages
// ──────────────────────────────────────────────

export interface TemperatureMessage {
  type: "temperature";
  timestamp_ms: number;
  et: number;
  bt: number;
  et_ror: number;
  bt_ror: number;
  extra_channels: Record<string, number>;
}

export interface EventMessage {
  type: "event";
  event_type: RoastEventType;
  timestamp_ms: number;
  auto_detected: boolean;
  bt_at_event: number;
  et_at_event: number;
}

export interface StateMessage {
  type: "state";
  state: SessionState;
  previous_state: SessionState;
}

export interface AlarmMessage {
  type: "alarm";
  alarm_id: string;
  message: string;
  severity: AlarmSeverity;
  timestamp_ms: number;
  bt: number;
  et: number;
}

export interface ReplayMessage {
  type: "replay";
  timestamp_ms: number;
  et: number;
  bt: number;
  et_ror: number;
  bt_ror: number;
  controls: Record<string, number>;
  progress_pct: number;
  total_duration_ms: number;
}

export interface ControlAckMessage {
  type: "control_ack";
  channel: string;
  value: number;
  applied: boolean;
  enabled: boolean;
  message: string;
}

export interface ErrorMessage {
  type: "error";
  code: string;
  message: string;
  recoverable: boolean;
}

export interface ConnectionMessage {
  type: "connection";
  driver_state: DriverState;
  driver_name: string;
  message: string;
}

export type ServerMessage =
  | TemperatureMessage
  | EventMessage
  | StateMessage
  | AlarmMessage
  | ReplayMessage
  | ControlAckMessage
  | ErrorMessage
  | ConnectionMessage;

// ──────────────────────────────────────────────
// Client → Server messages
// ──────────────────────────────────────────────

export interface ControlCommand {
  type: "control";
  channel: string;
  value: number; // 0.0 – 1.0
  enabled?: boolean;
}

export type CommandAction =
  | "start_monitoring"
  | "stop_monitoring"
  | "start_recording"
  | "stop_recording"
  | "mark_event"
  | "reset"
  | "sync";

export interface SessionCommand {
  type: "command";
  action: CommandAction;
  event_type?: RoastEventType; // required when action === 'mark_event'
  last_timestamp_ms?: number; // required when action === 'sync'
}

export type ReplayActionType = "start" | "pause" | "resume" | "stop" | "seek";

export interface ReplayControlCommand {
  type: "replay_control";
  action: ReplayActionType;
  profile_id?: string;
  speed?: number; // 0 < speed <= 10, default 1.0
  timestamp_ms?: number; // required when action === 'seek'
}

export type ClientMessage =
  | ControlCommand
  | SessionCommand
  | ReplayControlCommand;
