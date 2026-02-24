"""Pydantic models for WebSocket message serialization.

These models define the wire contract between backend and frontend.
Both sides MUST stay in sync — the TypeScript counterpart is at
frontend/src/lib/types/ws-messages.ts.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

# ──────────────────────────────────────────────
# Shared enums
# ──────────────────────────────────────────────

class RoastEventType(StrEnum):
    """Known roast event types."""

    CHARGE = "CHARGE"
    DRY_END = "DRY_END"
    FCs = "FCs"
    FCe = "FCe"
    SCs = "SCs"
    SCe = "SCe"
    DROP = "DROP"
    COOL = "COOL"
    TP = "TP"


class SessionStateValue(StrEnum):
    """Session state values matching core.session.SessionState."""

    IDLE = "idle"
    MONITORING = "monitoring"
    RECORDING = "recording"
    FINISHED = "finished"


class AlarmSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class DriverStateValue(StrEnum):
    """Driver connection states matching drivers.base.ConnectionState."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class CommandAction(StrEnum):
    START_MONITORING = "start_monitoring"
    STOP_MONITORING = "stop_monitoring"
    START_RECORDING = "start_recording"
    STOP_RECORDING = "stop_recording"
    MARK_EVENT = "mark_event"
    RESET = "reset"
    SYNC = "sync"


class ReplayAction(StrEnum):
    START = "start"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"
    SEEK = "seek"


# ──────────────────────────────────────────────
# Server → Client messages
# ──────────────────────────────────────────────

class TemperatureMessage(BaseModel):
    """Periodic temperature reading pushed at sampling interval."""

    type: Literal["temperature"] = "temperature"
    timestamp_ms: float = Field(ge=0)
    et: float
    bt: float
    et_ror: float = Field(default=0.0, description="ET rate of rise (C/min)")
    bt_ror: float = Field(default=0.0, description="BT rate of rise (C/min)")
    extra_channels: dict[str, float] = Field(default_factory=dict)


class EventMessage(BaseModel):
    """Roast event notification."""

    type: Literal["event"] = "event"
    event_type: RoastEventType
    timestamp_ms: float = Field(ge=0)
    auto_detected: bool = False
    bt_at_event: float = 0.0
    et_at_event: float = 0.0


class StateMessage(BaseModel):
    """Session state transition notification."""

    type: Literal["state"] = "state"
    state: SessionStateValue
    previous_state: SessionStateValue


class AlarmMessage(BaseModel):
    """Alarm trigger notification."""

    type: Literal["alarm"] = "alarm"
    alarm_id: str
    message: str
    severity: AlarmSeverity
    timestamp_ms: float = Field(ge=0)
    bt: float = 0.0
    et: float = 0.0


class ReplayMessage(BaseModel):
    """Profile replay data point."""

    type: Literal["replay"] = "replay"
    timestamp_ms: float = Field(ge=0)
    et: float
    bt: float
    et_ror: float = 0.0
    bt_ror: float = 0.0
    controls: dict[str, float] = Field(default_factory=dict)
    progress_pct: float = Field(ge=0, le=100)
    total_duration_ms: float = Field(ge=0)


class ControlAckMessage(BaseModel):
    """Acknowledgement of a control command."""

    type: Literal["control_ack"] = "control_ack"
    channel: str
    value: float
    applied: bool
    enabled: bool = True
    message: str = ""


class ErrorMessage(BaseModel):
    """Error notification (non-fatal)."""

    type: Literal["error"] = "error"
    code: str
    message: str
    recoverable: bool = True


class ConnectionMessage(BaseModel):
    """Driver connection state change."""

    type: Literal["connection"] = "connection"
    driver_state: DriverStateValue
    driver_name: str = ""
    message: str = ""


# Union type for dispatch
ServerMessage = (
    TemperatureMessage
    | EventMessage
    | StateMessage
    | AlarmMessage
    | ReplayMessage
    | ControlAckMessage
    | ErrorMessage
    | ConnectionMessage
)


# ──────────────────────────────────────────────
# Client → Server messages
# ──────────────────────────────────────────────

class ControlCommand(BaseModel):
    """Set a control slider value."""

    type: Literal["control"] = "control"
    channel: str
    value: float = Field(ge=0.0, le=1.0)
    enabled: bool = True


class SessionCommand(BaseModel):
    """Session lifecycle or event marking command."""

    type: Literal["command"] = "command"
    action: CommandAction
    event_type: RoastEventType | None = None  # required when action == mark_event
    last_timestamp_ms: float | None = None  # required when action == sync


class ReplayControlCommand(BaseModel):
    """Control profile replay playback."""

    type: Literal["replay_control"] = "replay_control"
    action: ReplayAction
    profile_id: str = ""
    speed: float = Field(default=1.0, gt=0, le=10.0)
    timestamp_ms: float | None = None  # required when action == seek


# Union type for dispatch
ClientMessage = ControlCommand | SessionCommand | ReplayControlCommand
