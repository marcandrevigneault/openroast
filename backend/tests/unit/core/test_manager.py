"""Unit tests for the MachineManager."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openroast.core.manager import MachineManager
from openroast.core.session import SessionState
from openroast.drivers.base import ConnectionState, DriverInfo, TemperatureReading
from openroast.models.catalog import (
    ControlConfig,
    ModbusConnectionConfig,
    ProtocolType,
)
from openroast.models.machine import SavedMachine
from openroast.models.ws_messages import (
    CommandAction,
    ControlAckMessage,
    ErrorMessage,
    SessionStateValue,
    StateMessage,
    TemperatureMessage,
)

# ── Helpers ───────────────────────────────────────────────────────────


def _make_machine(
    machine_id: str = "test-m1",
    name: str = "Test Machine",
    controls: list[ControlConfig] | None = None,
) -> SavedMachine:
    return SavedMachine(
        id=machine_id,
        name=name,
        protocol=ProtocolType.MODBUS_TCP,
        connection=ModbusConnectionConfig(type="modbus_tcp"),
        sampling_interval_ms=500,
        controls=controls or [],
    )


def _mock_driver(
    et: float = 210.0,
    bt: float = 155.0,
    extra: dict[str, float] | None = None,
) -> MagicMock:
    """Create a mock driver that returns predictable readings."""
    driver = MagicMock()
    driver.state = ConnectionState.CONNECTED
    driver.read_temperatures = AsyncMock(
        return_value=TemperatureReading(et=et, bt=bt, timestamp_ms=0.0)
    )
    driver.read_extra_channels = AsyncMock(return_value=extra or {})
    driver.write_control = AsyncMock()
    driver.connect = AsyncMock()
    driver.disconnect = AsyncMock()
    driver.info.return_value = DriverInfo(
        name="Mock Modbus", manufacturer="Test", model="M1", protocol="modbus_tcp"
    )
    # close() is sync in pymodbus
    driver.close = MagicMock()
    return driver


def _mock_storage(machines: dict[str, SavedMachine] | None = None) -> MagicMock:
    """Create a mock MachineStorage."""
    storage = MagicMock()
    machines = machines or {}
    storage.get.side_effect = lambda mid: machines.get(mid)
    return storage


# ── Constructor tests ─────────────────────────────────────────────────


class TestMachineManagerInit:
    def test_no_active_machines(self) -> None:
        manager = MachineManager(_mock_storage())
        assert manager.active_machines == []

    def test_get_instance_returns_none(self) -> None:
        manager = MachineManager(_mock_storage())
        assert manager.get_instance("nonexistent") is None


# ── Connect / Disconnect tests ────────────────────────────────────────


class TestConnectDisconnect:
    @patch("openroast.core.manager.create_driver")
    async def test_connect_machine(self, mock_factory: MagicMock) -> None:
        machine = _make_machine()
        storage = _mock_storage({machine.id: machine})
        mock_factory.return_value = _mock_driver()

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        assert machine.id in manager.active_machines
        instance = manager.get_instance(machine.id)
        assert instance is not None
        assert instance.machine.id == machine.id
        assert instance.sampling_task is not None

        # Clean up
        await manager.disconnect_machine(machine.id)

    @patch("openroast.core.manager.create_driver")
    async def test_connect_idempotent(self, mock_factory: MagicMock) -> None:
        machine = _make_machine()
        storage = _mock_storage({machine.id: machine})
        mock_factory.return_value = _mock_driver()

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)
        await manager.connect_machine(machine.id)  # No-op

        mock_factory.assert_called_once()
        await manager.disconnect_machine(machine.id)

    async def test_connect_unknown_machine_raises(self) -> None:
        manager = MachineManager(_mock_storage())

        with pytest.raises(ValueError, match="not found"):
            await manager.connect_machine("nonexistent")

    @patch("openroast.core.manager.create_driver")
    async def test_disconnect_machine(self, mock_factory: MagicMock) -> None:
        machine = _make_machine()
        storage = _mock_storage({machine.id: machine})
        driver = _mock_driver()
        mock_factory.return_value = driver

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)
        await manager.disconnect_machine(machine.id)

        assert machine.id not in manager.active_machines
        driver.disconnect.assert_awaited_once()

    async def test_disconnect_nonexistent_is_noop(self) -> None:
        manager = MachineManager(_mock_storage())
        await manager.disconnect_machine("nonexistent")  # No error


# ── Subscribe / Unsubscribe tests ─────────────────────────────────────


class TestSubscribe:
    @patch("openroast.core.manager.create_driver")
    async def test_subscribe_and_unsubscribe(
        self, mock_factory: MagicMock
    ) -> None:
        machine = _make_machine()
        storage = _mock_storage({machine.id: machine})
        mock_factory.return_value = _mock_driver()

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        ws = AsyncMock()
        await manager.subscribe(machine.id, ws)
        instance = manager.get_instance(machine.id)
        assert ws in instance.subscribers

        await manager.unsubscribe(machine.id, ws)
        assert ws not in instance.subscribers

        await manager.disconnect_machine(machine.id)

    async def test_subscribe_nonexistent_is_noop(self) -> None:
        manager = MachineManager(_mock_storage())
        ws = AsyncMock()
        await manager.subscribe("nonexistent", ws)  # No error
        await manager.unsubscribe("nonexistent", ws)  # No error


# ── Control handling tests ────────────────────────────────────────────


class TestHandleControl:
    @patch("openroast.core.manager.create_driver")
    async def test_scales_and_writes(self, mock_factory: MagicMock) -> None:
        machine = _make_machine(controls=[
            ControlConfig(
                name="Gas", channel="gas",
                command="writeSingle(1,47,{})", min=0, max=100,
            ),
        ])
        storage = _mock_storage({machine.id: machine})
        driver = _mock_driver()
        mock_factory.return_value = driver

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        ack = await manager.handle_control(machine.id, "gas", 0.5)

        assert isinstance(ack, ControlAckMessage)
        assert ack.applied is True
        assert ack.channel == "gas"
        # 0.5 * (100 - 0) + 0 = 50.0
        driver.write_control.assert_awaited_once_with("gas", 50.0)

        await manager.disconnect_machine(machine.id)

    @patch("openroast.core.manager.create_driver")
    async def test_scales_custom_range(self, mock_factory: MagicMock) -> None:
        """Test scaling with non-zero min (e.g., airflow 35-60 Hz)."""
        machine = _make_machine(controls=[
            ControlConfig(
                name="Air", channel="air",
                command="writeSingle(1,48,{})", min=35, max=60,
            ),
        ])
        storage = _mock_storage({machine.id: machine})
        driver = _mock_driver()
        mock_factory.return_value = driver

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        ack = await manager.handle_control(machine.id, "air", 0.5)

        assert ack.applied is True
        # 0.5 * (60 - 35) + 35 = 47.5
        driver.write_control.assert_awaited_once_with("air", 47.5)

        await manager.disconnect_machine(machine.id)

    async def test_control_not_connected(self) -> None:
        manager = MachineManager(_mock_storage())
        ack = await manager.handle_control("nonexistent", "gas", 0.5)

        assert ack.applied is False
        assert "not connected" in ack.message.lower()

    @patch("openroast.core.manager.create_driver")
    async def test_control_unknown_channel(
        self, mock_factory: MagicMock
    ) -> None:
        machine = _make_machine(controls=[])
        storage = _mock_storage({machine.id: machine})
        mock_factory.return_value = _mock_driver()

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        ack = await manager.handle_control(machine.id, "unknown", 0.5)
        assert ack.applied is False
        assert "Unknown control" in ack.message

        await manager.disconnect_machine(machine.id)

    @patch("openroast.core.manager.create_driver")
    async def test_control_driver_error(
        self, mock_factory: MagicMock
    ) -> None:
        machine = _make_machine(controls=[
            ControlConfig(
                name="Gas", channel="gas",
                command="writeSingle(1,47,{})", min=0, max=100,
            ),
        ])
        storage = _mock_storage({machine.id: machine})
        driver = _mock_driver()
        driver.write_control = AsyncMock(side_effect=ConnectionError("timeout"))
        mock_factory.return_value = driver

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        ack = await manager.handle_control(machine.id, "gas", 0.5)
        assert ack.applied is False
        assert "timeout" in ack.message

        await manager.disconnect_machine(machine.id)

    @patch("openroast.core.manager.create_driver")
    async def test_control_enabled_false_writes_zero(
        self, mock_factory: MagicMock
    ) -> None:
        """When enabled=False, driver receives 0 regardless of value."""
        machine = _make_machine(controls=[
            ControlConfig(
                name="Gas", channel="gas",
                command="writeSingle(1,47,{})", min=0, max=100,
            ),
        ])
        storage = _mock_storage({machine.id: machine})
        driver = _mock_driver()
        mock_factory.return_value = driver

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        ack = await manager.handle_control(machine.id, "gas", 0.7, enabled=False)

        assert ack.applied is True
        assert ack.enabled is False
        # Should write 0 to the driver, not 70
        driver.write_control.assert_awaited_once_with("gas", 0.0)

        await manager.disconnect_machine(machine.id)

    @patch("openroast.core.manager.create_driver")
    async def test_control_enabled_true_writes_scaled(
        self, mock_factory: MagicMock
    ) -> None:
        """When enabled=True (default), driver receives scaled value."""
        machine = _make_machine(controls=[
            ControlConfig(
                name="Gas", channel="gas",
                command="writeSingle(1,47,{})", min=0, max=100,
            ),
        ])
        storage = _mock_storage({machine.id: machine})
        driver = _mock_driver()
        mock_factory.return_value = driver

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        ack = await manager.handle_control(machine.id, "gas", 0.7, enabled=True)

        assert ack.applied is True
        assert ack.enabled is True
        # 0.7 * (100 - 0) + 0 = 70.0
        driver.write_control.assert_awaited_once_with("gas", 70.0)

        await manager.disconnect_machine(machine.id)

    @patch("openroast.core.manager.create_driver")
    async def test_control_enabled_tracks_state(
        self, mock_factory: MagicMock
    ) -> None:
        """control_enabled dict tracks per-channel enabled state."""
        machine = _make_machine(controls=[
            ControlConfig(
                name="Gas", channel="gas",
                command="writeSingle(1,47,{})", min=0, max=100,
            ),
        ])
        storage = _mock_storage({machine.id: machine})
        driver = _mock_driver()
        mock_factory.return_value = driver

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)
        instance = manager._instances[machine.id]

        # Disable the channel
        await manager.handle_control(machine.id, "gas", 0.5, enabled=False)
        assert instance.control_enabled["gas"] is False

        # Re-enable the channel
        await manager.handle_control(machine.id, "gas", 0.5, enabled=True)
        assert instance.control_enabled["gas"] is True

        await manager.disconnect_machine(machine.id)


# ── Session command tests ─────────────────────────────────────────────


class TestHandleSessionCommand:
    @patch("openroast.core.manager.create_driver")
    async def test_start_monitoring(self, mock_factory: MagicMock) -> None:
        machine = _make_machine()
        storage = _mock_storage({machine.id: machine})
        mock_factory.return_value = _mock_driver()

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        result = await manager.handle_session_command(
            machine.id, CommandAction.START_MONITORING
        )

        assert isinstance(result, StateMessage)
        assert result.state == SessionStateValue.MONITORING
        assert result.previous_state == SessionStateValue.IDLE

        await manager.disconnect_machine(machine.id)

    @patch("openroast.core.manager.create_driver")
    async def test_stop_monitoring(self, mock_factory: MagicMock) -> None:
        machine = _make_machine()
        storage = _mock_storage({machine.id: machine})
        mock_factory.return_value = _mock_driver()

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        # IDLE → MONITORING
        await manager.handle_session_command(
            machine.id, CommandAction.START_MONITORING
        )

        # MONITORING → IDLE
        result = await manager.handle_session_command(
            machine.id, CommandAction.STOP_MONITORING
        )

        assert isinstance(result, StateMessage)
        assert result.state == SessionStateValue.IDLE
        assert result.previous_state == SessionStateValue.MONITORING

        await manager.disconnect_machine(machine.id)

    @patch("openroast.core.manager.create_driver")
    async def test_full_lifecycle(self, mock_factory: MagicMock) -> None:
        machine = _make_machine()
        storage = _mock_storage({machine.id: machine})
        mock_factory.return_value = _mock_driver()

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        # IDLE → MONITORING
        r1 = await manager.handle_session_command(
            machine.id, CommandAction.START_MONITORING
        )
        assert isinstance(r1, StateMessage)
        assert r1.state == SessionStateValue.MONITORING

        # MONITORING → RECORDING
        r2 = await manager.handle_session_command(
            machine.id, CommandAction.START_RECORDING
        )
        assert isinstance(r2, StateMessage)
        assert r2.state == SessionStateValue.RECORDING

        # RECORDING → FINISHED
        r3 = await manager.handle_session_command(
            machine.id, CommandAction.STOP_RECORDING
        )
        assert isinstance(r3, StateMessage)
        assert r3.state == SessionStateValue.FINISHED

        await manager.disconnect_machine(machine.id)

    @patch("openroast.core.manager.create_driver")
    async def test_start_monitoring_clears_ring_buffer(
        self, mock_factory: MagicMock
    ) -> None:
        """Ring buffer is cleared on start_monitoring to prevent stale data replay."""
        machine = _make_machine()
        storage = _mock_storage({machine.id: machine})
        mock_factory.return_value = _mock_driver()

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        # Let some data accumulate
        await asyncio.sleep(0.6)
        instance = manager.get_instance(machine.id)
        assert len(instance.ring_buffer) >= 1

        # Start monitoring — should clear ring buffer
        await manager.handle_session_command(
            machine.id, CommandAction.START_MONITORING
        )
        assert len(instance.ring_buffer) == 0

        await manager.disconnect_machine(machine.id)

    @patch("openroast.core.manager.create_driver")
    async def test_start_recording_clears_ring_buffer(
        self, mock_factory: MagicMock
    ) -> None:
        """Ring buffer is cleared on start_recording to prevent stale data replay."""
        machine = _make_machine()
        storage = _mock_storage({machine.id: machine})
        mock_factory.return_value = _mock_driver()

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        # Move to monitoring and let data accumulate
        await manager.handle_session_command(
            machine.id, CommandAction.START_MONITORING
        )
        await asyncio.sleep(0.6)
        instance = manager.get_instance(machine.id)
        assert len(instance.ring_buffer) >= 1

        # Start recording — should clear ring buffer
        await manager.handle_session_command(
            machine.id, CommandAction.START_RECORDING
        )
        assert len(instance.ring_buffer) == 0

        await manager.disconnect_machine(machine.id)

    @patch("openroast.core.manager.create_driver")
    async def test_start_recording_resets_clock(
        self, mock_factory: MagicMock
    ) -> None:
        machine = _make_machine()
        storage = _mock_storage({machine.id: machine})
        mock_factory.return_value = _mock_driver()

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        # Start monitoring — captures initial clock
        await manager.handle_session_command(
            machine.id, CommandAction.START_MONITORING
        )
        instance = manager._instances[machine.id]
        monitoring_clock = instance.start_time_ms

        # Start recording — clock must be reset
        await manager.handle_session_command(
            machine.id, CommandAction.START_RECORDING
        )
        assert instance.start_time_ms >= monitoring_clock
        assert instance.prev_et is None
        assert instance.prev_bt is None

        await manager.disconnect_machine(machine.id)

    @patch("openroast.core.manager.create_driver")
    async def test_invalid_state_transition(
        self, mock_factory: MagicMock
    ) -> None:
        machine = _make_machine()
        storage = _mock_storage({machine.id: machine})
        mock_factory.return_value = _mock_driver()

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        # Try to record from IDLE (should fail)
        result = await manager.handle_session_command(
            machine.id, CommandAction.START_RECORDING
        )
        assert isinstance(result, ErrorMessage)
        assert result.code == "INVALID_STATE_TRANSITION"

        await manager.disconnect_machine(machine.id)

    @patch("openroast.core.manager.create_driver")
    async def test_reset_command(self, mock_factory: MagicMock) -> None:
        machine = _make_machine()
        storage = _mock_storage({machine.id: machine})
        mock_factory.return_value = _mock_driver()

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        # Move to monitoring first
        await manager.handle_session_command(
            machine.id, CommandAction.START_MONITORING
        )

        # Reset back to IDLE
        result = await manager.handle_session_command(
            machine.id, CommandAction.RESET
        )
        assert isinstance(result, StateMessage)
        assert result.state == SessionStateValue.IDLE

        # Session is fresh
        instance = manager.get_instance(machine.id)
        assert instance.session.state == SessionState.IDLE

        await manager.disconnect_machine(machine.id)

    async def test_command_not_connected(self) -> None:
        manager = MachineManager(_mock_storage())
        result = await manager.handle_session_command(
            "nonexistent", CommandAction.START_MONITORING
        )
        assert isinstance(result, ErrorMessage)
        assert result.code == "MACHINE_NOT_FOUND"

    @patch("openroast.core.manager.create_driver")
    async def test_mark_event_requires_event_type(
        self, mock_factory: MagicMock
    ) -> None:
        machine = _make_machine()
        storage = _mock_storage({machine.id: machine})
        mock_factory.return_value = _mock_driver()

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        # Move to recording
        await manager.handle_session_command(
            machine.id, CommandAction.START_MONITORING
        )
        await manager.handle_session_command(
            machine.id, CommandAction.START_RECORDING
        )

        # Mark event without type
        result = await manager.handle_session_command(
            machine.id, CommandAction.MARK_EVENT, event_type=None
        )
        assert isinstance(result, ErrorMessage)
        assert "event_type required" in result.message

        await manager.disconnect_machine(machine.id)


# ── RoR computation tests ────────────────────────────────────────────


class TestComputeRor:
    def test_first_reading(self) -> None:
        assert MachineManager._compute_ror(210.0, None, 1.0) == 0.0

    def test_rising_temperature(self) -> None:
        # 2°C rise over 2 seconds = 60°C/min
        ror = MachineManager._compute_ror(212.0, 210.0, 2.0)
        assert ror == pytest.approx(60.0)

    def test_falling_temperature(self) -> None:
        # 1°C drop over 1 second = -60°C/min
        ror = MachineManager._compute_ror(209.0, 210.0, 1.0)
        assert ror == pytest.approx(-60.0)

    def test_zero_interval(self) -> None:
        assert MachineManager._compute_ror(210.0, 200.0, 0.0) == 0.0


# ── Scale to native tests ────────────────────────────────────────────


class TestScaleToNative:
    def test_zero(self) -> None:
        control = ControlConfig(
            name="Gas", channel="gas", min=0, max=100,
        )
        assert MachineManager._scale_to_native(control, 0.0) == pytest.approx(0.0)

    def test_one(self) -> None:
        control = ControlConfig(
            name="Gas", channel="gas", min=0, max=100,
        )
        assert MachineManager._scale_to_native(control, 1.0) == pytest.approx(100.0)

    def test_midpoint(self) -> None:
        control = ControlConfig(
            name="Air", channel="air", min=35, max=60,
        )
        assert MachineManager._scale_to_native(control, 0.5) == pytest.approx(47.5)

    def test_non_zero_min(self) -> None:
        control = ControlConfig(
            name="Power", channel="power", min=80, max=150,
        )
        # 0.0 → 80, 1.0 → 150, 0.25 → 97.5
        assert MachineManager._scale_to_native(control, 0.25) == pytest.approx(97.5)


# ── Sampling loop tests ──────────────────────────────────────────────


class TestSamplingLoop:
    @patch("openroast.core.manager.create_driver")
    async def test_broadcasts_temperature(
        self, mock_factory: MagicMock
    ) -> None:
        """Sampling loop reads from driver and broadcasts to subscribers."""
        machine = _make_machine()
        storage = _mock_storage({machine.id: machine})
        driver = _mock_driver(et=210.0, bt=155.0, extra={"Inlet": 180.0})
        mock_factory.return_value = driver

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        ws = AsyncMock()
        await manager.subscribe(machine.id, ws)

        # Let the sampling loop run for a bit
        await asyncio.sleep(0.6)

        # Should have received temperature messages
        assert ws.send_json.call_count >= 1
        sent_data = ws.send_json.call_args_list[0][0][0]
        assert sent_data["type"] == "temperature"
        assert sent_data["et"] == pytest.approx(210.0)
        assert sent_data["bt"] == pytest.approx(155.0)
        assert sent_data["extra_channels"] == {"Inlet": 180.0}

        await manager.disconnect_machine(machine.id)

    @patch("openroast.core.manager.create_driver")
    async def test_ring_buffer_stores_messages(
        self, mock_factory: MagicMock
    ) -> None:
        machine = _make_machine()
        storage = _mock_storage({machine.id: machine})
        mock_factory.return_value = _mock_driver()

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        # Let it run briefly
        await asyncio.sleep(0.6)

        instance = manager.get_instance(machine.id)
        assert len(instance.ring_buffer) >= 1
        assert all(isinstance(m, TemperatureMessage) for m in instance.ring_buffer)

        await manager.disconnect_machine(machine.id)

    @patch("openroast.core.manager.create_driver")
    async def test_computes_ror(self, mock_factory: MagicMock) -> None:
        """RoR should be non-zero after multiple readings with changing temps."""
        call_count = 0

        async def varying_temps(**_: object) -> TemperatureReading:
            nonlocal call_count
            call_count += 1
            # Temperature rises by 1°C per reading
            return TemperatureReading(
                et=200.0 + call_count, bt=150.0 + call_count, timestamp_ms=0.0
            )

        machine = _make_machine()
        storage = _mock_storage({machine.id: machine})
        driver = _mock_driver()
        driver.read_temperatures = varying_temps
        mock_factory.return_value = driver

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        ws = AsyncMock()
        await manager.subscribe(machine.id, ws)

        # Wait for at least 2 readings
        await asyncio.sleep(1.1)

        # Find the second+ message which should have non-zero RoR
        calls = ws.send_json.call_args_list
        if len(calls) >= 2:
            second_msg = calls[1][0][0]
            assert second_msg["bt_ror"] != 0.0

        await manager.disconnect_machine(machine.id)

    @patch("openroast.core.manager.create_driver")
    async def test_connection_error_handling(
        self, mock_factory: MagicMock
    ) -> None:
        """Consecutive connection errors stop the sampling loop."""
        machine = _make_machine()
        storage = _mock_storage({machine.id: machine})
        driver = _mock_driver()
        driver.read_temperatures = AsyncMock(
            side_effect=ConnectionError("timeout")
        )
        mock_factory.return_value = driver

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        ws = AsyncMock()
        await manager.subscribe(machine.id, ws)

        # Wait for errors to accumulate (5 errors at 500ms interval = ~2.5s)
        await asyncio.sleep(3.0)

        # Should have received error messages and a final connection error
        sent = [c[0][0] for c in ws.send_json.call_args_list]
        error_msgs = [m for m in sent if m["type"] == "error"]
        conn_msgs = [m for m in sent if m["type"] == "connection"]

        assert len(error_msgs) >= 1
        assert len(conn_msgs) >= 1
        assert conn_msgs[-1]["driver_state"] == "error"

        await manager.disconnect_machine(machine.id)

    @patch("openroast.core.manager.create_driver")
    async def test_dead_subscriber_removed(
        self, mock_factory: MagicMock
    ) -> None:
        """Subscribers that error on send are removed."""
        machine = _make_machine()
        storage = _mock_storage({machine.id: machine})
        mock_factory.return_value = _mock_driver()

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        ws = AsyncMock()
        ws.send_json = AsyncMock(side_effect=Exception("disconnected"))
        await manager.subscribe(machine.id, ws)

        # Let sampling run to trigger broadcast
        await asyncio.sleep(0.6)

        instance = manager.get_instance(machine.id)
        assert ws not in instance.subscribers

        await manager.disconnect_machine(machine.id)


# ── Sync messages tests ──────────────────────────────────────────────


class TestSyncMessages:
    @patch("openroast.core.manager.create_driver")
    async def test_get_sync_messages(self, mock_factory: MagicMock) -> None:
        machine = _make_machine()
        storage = _mock_storage({machine.id: machine})
        mock_factory.return_value = _mock_driver()

        manager = MachineManager(storage)
        await manager.connect_machine(machine.id)

        # Wait for some data to accumulate
        await asyncio.sleep(1.1)

        instance = manager.get_instance(machine.id)
        if len(instance.ring_buffer) >= 2:
            # Get messages since the first one
            first_ts = instance.ring_buffer[0].timestamp_ms
            msgs = manager.get_sync_messages(machine.id, first_ts)
            assert all(m.timestamp_ms > first_ts for m in msgs)

        await manager.disconnect_machine(machine.id)

    def test_sync_nonexistent_machine(self) -> None:
        manager = MachineManager(_mock_storage())
        assert manager.get_sync_messages("nonexistent", 0.0) == []
