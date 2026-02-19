"""WebSocket endpoint for real-time roast data streaming."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from openroast.models.ws_messages import (
    CommandAction,
    ConnectionMessage,
    DriverStateValue,
    ErrorMessage,
    SessionStateValue,
)

if TYPE_CHECKING:
    from openroast.core.manager import MachineManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Set by init_manager() at startup
_manager: MachineManager | None = None


def init_manager(manager: MachineManager) -> None:
    """Configure the machine manager for the WebSocket handler."""
    global _manager
    _manager = manager


def _get_manager() -> MachineManager:
    if _manager is None:
        raise RuntimeError("MachineManager not initialised")
    return _manager


@router.websocket("/live/{machine_id}")
async def live_data(websocket: WebSocket, machine_id: str) -> None:
    """Stream live temperature data for a machine.

    Protocol:
      - Client connects to /ws/live/{machine_id}
      - Server pushes JSON messages at the sampling interval via subscription
      - Client can send control commands and session commands as JSON

    Server -> Client messages (pushed via subscription):
      {"type": "temperature", "et": 210.5, "bt": 155.2, ...}
      {"type": "state", "state": "recording", ...}
      {"type": "error", ...}
      {"type": "connection", ...}

    Client -> Server messages:
      {"type": "control", "channel": "burner", "value": 0.8}
      {"type": "command", "action": "start_recording"}
      {"type": "command", "action": "sync", "last_timestamp_ms": 5000}
    """
    manager = _get_manager()
    await websocket.accept()

    # Check if machine is connected
    instance = manager.get_instance(machine_id)
    if instance is None:
        error = ErrorMessage(
            code="MACHINE_NOT_FOUND",
            message=f"Machine '{machine_id}' is not connected",
            recoverable=False,
        )
        await websocket.send_json(error.model_dump())
        await websocket.close(code=4004)
        return

    # Send current connection state
    conn_msg = ConnectionMessage(
        driver_state=DriverStateValue.CONNECTED,
        driver_name=instance.driver.info().name,
        message="Connected",
    )
    await websocket.send_json(conn_msg.model_dump())

    # Send current session state
    from openroast.models.ws_messages import StateMessage

    state_msg = StateMessage(
        state=SessionStateValue(instance.session.state.value),
        previous_state=SessionStateValue(instance.session.state.value),
    )
    await websocket.send_json(state_msg.model_dump())

    # Register as subscriber (will receive temperature broadcasts)
    await manager.subscribe(machine_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "control":
                await _handle_control(manager, machine_id, websocket, data)
            elif msg_type == "command":
                await _handle_command(manager, machine_id, websocket, data)
            else:
                error = ErrorMessage(
                    code="INVALID_MESSAGE",
                    message=f"Unknown message type: {msg_type}",
                )
                await websocket.send_json(error.model_dump())
    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected from machine %s", machine_id)
    except Exception:
        logger.exception("WebSocket error for machine %s", machine_id)
    finally:
        await manager.unsubscribe(machine_id, websocket)


async def _handle_control(
    manager: MachineManager,
    machine_id: str,
    ws: WebSocket,
    data: dict,
) -> None:
    """Process a control command from the client."""
    channel = data.get("channel", "")
    value = data.get("value", 0.0)

    try:
        value = float(value)
    except (TypeError, ValueError):
        error = ErrorMessage(
            code="INVALID_MESSAGE",
            message=f"Invalid control value: {data.get('value')}",
        )
        await ws.send_json(error.model_dump())
        return

    if not 0.0 <= value <= 1.0:
        error = ErrorMessage(
            code="INVALID_MESSAGE",
            message=f"Control value must be 0.0-1.0, got {value}",
        )
        await ws.send_json(error.model_dump())
        return

    ack = await manager.handle_control(machine_id, channel, value)
    await ws.send_json(ack.model_dump())


async def _handle_command(
    manager: MachineManager,
    machine_id: str,
    ws: WebSocket,
    data: dict,
) -> None:
    """Process a session command from the client."""
    action_str = data.get("action", "")

    try:
        action = CommandAction(action_str)
    except ValueError:
        error = ErrorMessage(
            code="INVALID_MESSAGE",
            message=f"Unknown action: {action_str}",
        )
        await ws.send_json(error.model_dump())
        return

    # Handle sync specially — replay buffered messages
    if action == CommandAction.SYNC:
        last_ts = data.get("last_timestamp_ms", 0.0)
        try:
            last_ts = float(last_ts)
        except (TypeError, ValueError):
            last_ts = 0.0

        messages = manager.get_sync_messages(machine_id, last_ts)
        for msg in messages:
            await ws.send_json(msg.model_dump())
        return

    event_type = data.get("event_type")
    result = await manager.handle_session_command(machine_id, action, event_type)

    # Broadcast state changes to all subscribers
    from openroast.models.ws_messages import StateMessage

    if isinstance(result, StateMessage):
        instance = manager.get_instance(machine_id)
        if instance:
            for sub_ws in list(instance.subscribers):
                if sub_ws is not ws:
                    try:
                        await sub_ws.send_json(result.model_dump())
                    except Exception:
                        instance.subscribers.discard(sub_ws)

    await ws.send_json(result.model_dump())
