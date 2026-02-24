"""Unit tests for the WebSocket live data handler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from openroast.core.session import RoastSession
from openroast.drivers.base import DriverInfo
from openroast.models.ws_messages import (
    CommandAction,
    ControlAckMessage,
    SessionStateValue,
    StateMessage,
)
from openroast.ws.live import init_manager, router

# ── Helpers ───────────────────────────────────────────────────────────


def _make_mock_manager() -> MagicMock:
    """Create a mock MachineManager."""
    manager = MagicMock()
    manager.subscribe = AsyncMock()
    manager.unsubscribe = AsyncMock()
    manager.handle_control = AsyncMock()
    manager.handle_session_command = AsyncMock()
    manager.get_sync_messages = MagicMock(return_value=[])
    return manager


def _make_mock_instance() -> MagicMock:
    """Create a mock MachineInstance."""
    instance = MagicMock()
    driver = MagicMock()
    driver.info.return_value = DriverInfo(
        name="Mock Driver",
        manufacturer="Test",
        model="Test Model",
        protocol="mock",
    )
    instance.driver = driver
    instance.session = RoastSession(machine_name="Test")
    instance.subscribers = set()
    return instance


def _create_test_app(manager: MagicMock) -> FastAPI:
    """Create a FastAPI app with the WS router and mock manager."""
    app = FastAPI()
    app.include_router(router, prefix="/ws")
    init_manager(manager)
    return app


# ── Tests: Connection ─────────────────────────────────────────────────


class TestWebSocketConnect:
    """Tests for WebSocket connection handshake."""

    def test_machine_not_connected_returns_error(self) -> None:
        """When machine_id is not in the manager, send error and close."""
        manager = _make_mock_manager()
        manager.get_instance.return_value = None

        app = _create_test_app(manager)
        client = TestClient(app)

        with client.websocket_connect("/ws/live/unknown-machine") as ws:
            # First message should be error
            data = ws.receive_json()
            assert data["type"] == "error"
            assert data["code"] == "MACHINE_NOT_FOUND"
            assert data["recoverable"] is False

    def test_sends_initial_connection_and_state(self) -> None:
        """On connect, sends ConnectionMessage then StateMessage."""
        manager = _make_mock_manager()
        instance = _make_mock_instance()
        manager.get_instance.return_value = instance

        app = _create_test_app(manager)
        client = TestClient(app)

        with client.websocket_connect("/ws/live/m1") as ws:
            # First: connection message
            conn = ws.receive_json()
            assert conn["type"] == "connection"
            assert conn["driver_state"] == "connected"
            assert conn["driver_name"] == "Mock Driver"

            # Second: state message
            state = ws.receive_json()
            assert state["type"] == "state"
            assert state["state"] == "idle"

    def test_subscribes_and_unsubscribes(self) -> None:
        """Manager subscribe/unsubscribe are called correctly."""
        manager = _make_mock_manager()
        instance = _make_mock_instance()
        manager.get_instance.return_value = instance

        app = _create_test_app(manager)
        client = TestClient(app)

        with client.websocket_connect("/ws/live/m1") as ws:
            # Consume initial messages
            ws.receive_json()
            ws.receive_json()

            # Subscribe should have been called
            manager.subscribe.assert_called_once()
            assert manager.subscribe.call_args[0][0] == "m1"

        # After disconnect, unsubscribe should be called
        manager.unsubscribe.assert_called_once()
        assert manager.unsubscribe.call_args[0][0] == "m1"


# ── Tests: Control Commands ──────────────────────────────────────────


class TestWebSocketControl:
    """Tests for control command handling."""

    def test_valid_control_command(self) -> None:
        """Valid control command returns ControlAckMessage."""
        manager = _make_mock_manager()
        instance = _make_mock_instance()
        manager.get_instance.return_value = instance
        manager.handle_control.return_value = ControlAckMessage(
            channel="burner", value=0.8, applied=True,
        )

        app = _create_test_app(manager)
        client = TestClient(app)

        with client.websocket_connect("/ws/live/m1") as ws:
            ws.receive_json()  # connection
            ws.receive_json()  # state

            ws.send_json({"type": "control", "channel": "burner", "value": 0.8})
            ack = ws.receive_json()

            assert ack["type"] == "control_ack"
            assert ack["channel"] == "burner"
            assert ack["applied"] is True

        manager.handle_control.assert_called_once_with("m1", "burner", 0.8, enabled=True)

    def test_control_value_out_of_range(self) -> None:
        """Control value > 1.0 returns error."""
        manager = _make_mock_manager()
        instance = _make_mock_instance()
        manager.get_instance.return_value = instance

        app = _create_test_app(manager)
        client = TestClient(app)

        with client.websocket_connect("/ws/live/m1") as ws:
            ws.receive_json()
            ws.receive_json()

            ws.send_json({"type": "control", "channel": "burner", "value": 1.5})
            err = ws.receive_json()

            assert err["type"] == "error"
            assert err["code"] == "INVALID_MESSAGE"

    def test_control_invalid_value_type(self) -> None:
        """Non-numeric control value returns error."""
        manager = _make_mock_manager()
        instance = _make_mock_instance()
        manager.get_instance.return_value = instance

        app = _create_test_app(manager)
        client = TestClient(app)

        with client.websocket_connect("/ws/live/m1") as ws:
            ws.receive_json()
            ws.receive_json()

            ws.send_json({"type": "control", "channel": "burner", "value": "abc"})
            err = ws.receive_json()

            assert err["type"] == "error"
            assert err["code"] == "INVALID_MESSAGE"


# ── Tests: Session Commands ──────────────────────────────────────────


class TestWebSocketSessionCommand:
    """Tests for session command handling."""

    def test_start_monitoring(self) -> None:
        """Start monitoring command returns state message."""
        manager = _make_mock_manager()
        instance = _make_mock_instance()
        manager.get_instance.return_value = instance
        manager.handle_session_command.return_value = StateMessage(
            state=SessionStateValue.MONITORING,
            previous_state=SessionStateValue.IDLE,
        )

        app = _create_test_app(manager)
        client = TestClient(app)

        with client.websocket_connect("/ws/live/m1") as ws:
            ws.receive_json()
            ws.receive_json()

            ws.send_json({"type": "command", "action": "start_monitoring"})
            result = ws.receive_json()

            assert result["type"] == "state"
            assert result["state"] == "monitoring"

        manager.handle_session_command.assert_called_once_with(
            "m1", CommandAction.START_MONITORING, None,
        )

    def test_unknown_action(self) -> None:
        """Unknown action returns error."""
        manager = _make_mock_manager()
        instance = _make_mock_instance()
        manager.get_instance.return_value = instance

        app = _create_test_app(manager)
        client = TestClient(app)

        with client.websocket_connect("/ws/live/m1") as ws:
            ws.receive_json()
            ws.receive_json()

            ws.send_json({"type": "command", "action": "explode"})
            err = ws.receive_json()

            assert err["type"] == "error"
            assert err["code"] == "INVALID_MESSAGE"

    def test_mark_event_with_type(self) -> None:
        """Mark event passes event_type to manager."""
        manager = _make_mock_manager()
        instance = _make_mock_instance()
        manager.get_instance.return_value = instance
        manager.handle_session_command.return_value = StateMessage(
            state=SessionStateValue.RECORDING,
            previous_state=SessionStateValue.RECORDING,
        )

        app = _create_test_app(manager)
        client = TestClient(app)

        with client.websocket_connect("/ws/live/m1") as ws:
            ws.receive_json()
            ws.receive_json()

            ws.send_json({
                "type": "command",
                "action": "mark_event",
                "event_type": "CHARGE",
            })
            ws.receive_json()

        manager.handle_session_command.assert_called_once_with(
            "m1", CommandAction.MARK_EVENT, "CHARGE",
        )

    def test_sync_replays_buffer(self) -> None:
        """Sync command replays buffered messages."""
        manager = _make_mock_manager()
        instance = _make_mock_instance()
        manager.get_instance.return_value = instance

        from openroast.models.ws_messages import TemperatureMessage

        buffered = [
            TemperatureMessage(timestamp_ms=1000.0, et=180.0, bt=150.0),
            TemperatureMessage(timestamp_ms=1500.0, et=185.0, bt=155.0),
        ]
        manager.get_sync_messages.return_value = buffered

        app = _create_test_app(manager)
        client = TestClient(app)

        with client.websocket_connect("/ws/live/m1") as ws:
            ws.receive_json()  # connection
            ws.receive_json()  # state

            ws.send_json({
                "type": "command",
                "action": "sync",
                "last_timestamp_ms": 500.0,
            })

            msg1 = ws.receive_json()
            msg2 = ws.receive_json()

            assert msg1["type"] == "temperature"
            assert msg1["timestamp_ms"] == 1000.0
            assert msg2["type"] == "temperature"
            assert msg2["timestamp_ms"] == 1500.0

        manager.get_sync_messages.assert_called_once_with("m1", 500.0)


# ── Tests: Unknown Message Type ──────────────────────────────────────


class TestWebSocketUnknownMessage:
    """Tests for unknown message type handling."""

    def test_unknown_type_returns_error(self) -> None:
        """Unknown message type returns error."""
        manager = _make_mock_manager()
        instance = _make_mock_instance()
        manager.get_instance.return_value = instance

        app = _create_test_app(manager)
        client = TestClient(app)

        with client.websocket_connect("/ws/live/m1") as ws:
            ws.receive_json()
            ws.receive_json()

            ws.send_json({"type": "bogus", "data": 123})
            err = ws.receive_json()

            assert err["type"] == "error"
            assert err["code"] == "INVALID_MESSAGE"
            assert "bogus" in err["message"]
