"""Unit tests for WebSocket message models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from openroast.models.ws_messages import (
    AlarmMessage,
    AlarmSeverity,
    CommandAction,
    ConnectionMessage,
    ControlAckMessage,
    ControlCommand,
    DriverStateValue,
    ErrorMessage,
    EventMessage,
    ReplayControlCommand,
    ReplayMessage,
    RoastEventType,
    SessionCommand,
    SessionStateValue,
    StateMessage,
    TemperatureMessage,
)


class TestTemperatureMessage:
    def test_minimal(self) -> None:
        m = TemperatureMessage(timestamp_ms=3000, et=210.5, bt=185.3)
        assert m.type == "temperature"
        assert m.et_ror == 0.0
        assert m.extra_channels == {}

    def test_full(self) -> None:
        m = TemperatureMessage(
            timestamp_ms=45000, et=210.5, bt=185.3,
            et_ror=8.2, bt_ror=12.4,
            extra_channels={"inlet": 305.0},
        )
        assert m.extra_channels["inlet"] == 305.0

    def test_negative_timestamp_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TemperatureMessage(timestamp_ms=-1, et=200, bt=150)

    def test_serialization_roundtrip(self) -> None:
        m = TemperatureMessage(timestamp_ms=3000, et=210, bt=185)
        data = m.model_dump()
        assert data["type"] == "temperature"
        m2 = TemperatureMessage.model_validate(data)
        assert m2.et == m.et


class TestEventMessage:
    def test_charge_event(self) -> None:
        m = EventMessage(
            event_type=RoastEventType.CHARGE,
            timestamp_ms=5000,
            auto_detected=True,
            bt_at_event=155.2,
            et_at_event=210.5,
        )
        assert m.type == "event"
        assert m.event_type == "CHARGE"

    def test_all_event_types(self) -> None:
        for evt in RoastEventType:
            m = EventMessage(event_type=evt, timestamp_ms=0)
            assert m.event_type == evt


class TestStateMessage:
    def test_state_transition(self) -> None:
        m = StateMessage(
            state=SessionStateValue.RECORDING,
            previous_state=SessionStateValue.MONITORING,
        )
        assert m.type == "state"
        assert m.state == "recording"

    def test_all_states(self) -> None:
        for s in SessionStateValue:
            assert s.value in ("idle", "monitoring", "recording", "finished")


class TestAlarmMessage:
    def test_warning(self) -> None:
        m = AlarmMessage(
            alarm_id="high_bt",
            message="BT exceeded 230C",
            severity=AlarmSeverity.WARNING,
            timestamp_ms=120000,
            bt=231.2,
            et=285.0,
        )
        assert m.severity == "warning"


class TestReplayMessage:
    def test_progress_bounds(self) -> None:
        m = ReplayMessage(
            timestamp_ms=3000, et=200, bt=150,
            progress_pct=50.0, total_duration_ms=600000,
        )
        assert m.progress_pct == 50.0

    def test_progress_over_100_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReplayMessage(
                timestamp_ms=0, et=200, bt=150,
                progress_pct=101.0, total_duration_ms=600000,
            )


class TestControlAckMessage:
    def test_applied(self) -> None:
        m = ControlAckMessage(channel="burner", value=0.8, applied=True)
        assert m.type == "control_ack"
        assert m.message == ""

    def test_rejected(self) -> None:
        m = ControlAckMessage(
            channel="burner", value=0.8, applied=False,
            message="Driver does not support control",
        )
        assert not m.applied


class TestErrorMessage:
    def test_recoverable(self) -> None:
        m = ErrorMessage(code="DRIVER_READ_FAILED", message="timeout")
        assert m.recoverable is True

    def test_non_recoverable(self) -> None:
        m = ErrorMessage(
            code="MACHINE_NOT_FOUND", message="no such machine",
            recoverable=False,
        )
        assert not m.recoverable


class TestConnectionMessage:
    def test_connected(self) -> None:
        m = ConnectionMessage(
            driver_state=DriverStateValue.CONNECTED,
            driver_name="Modbus RTU",
        )
        assert m.type == "connection"
        assert m.driver_state == "connected"


class TestControlCommand:
    def test_valid(self) -> None:
        m = ControlCommand(channel="burner", value=0.8)
        assert m.type == "control"

    def test_value_bounds(self) -> None:
        with pytest.raises(ValidationError):
            ControlCommand(channel="burner", value=1.5)
        with pytest.raises(ValidationError):
            ControlCommand(channel="burner", value=-0.1)


class TestSessionCommand:
    def test_start_recording(self) -> None:
        m = SessionCommand(action=CommandAction.START_RECORDING)
        assert m.type == "command"
        assert m.event_type is None

    def test_mark_event(self) -> None:
        m = SessionCommand(
            action=CommandAction.MARK_EVENT,
            event_type=RoastEventType.FCs,
        )
        assert m.event_type == "FCs"

    def test_sync(self) -> None:
        m = SessionCommand(
            action=CommandAction.SYNC,
            last_timestamp_ms=45000,
        )
        assert m.last_timestamp_ms == 45000


class TestReplayControlCommand:
    def test_start(self) -> None:
        m = ReplayControlCommand(
            action="start", profile_id="abc-123", speed=2.0,
        )
        assert m.type == "replay_control"
        assert m.speed == 2.0

    def test_speed_bounds(self) -> None:
        with pytest.raises(ValidationError):
            ReplayControlCommand(action="start", speed=0)
        with pytest.raises(ValidationError):
            ReplayControlCommand(action="start", speed=11)

    def test_seek(self) -> None:
        m = ReplayControlCommand(
            action="seek", timestamp_ms=60000,
        )
        assert m.timestamp_ms == 60000
