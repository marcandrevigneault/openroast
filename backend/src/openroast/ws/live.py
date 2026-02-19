"""WebSocket endpoint for real-time roast data streaming."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/live/{machine_id}")
async def live_data(websocket: WebSocket, machine_id: str) -> None:
    """Stream live temperature data for a machine.

    Protocol:
      - Client connects to /ws/live/{machine_id}
      - Server pushes JSON messages at the sampling interval
      - Client can send control commands as JSON

    Server → Client messages:
      {"type": "temperature", "et": 210.5, "bt": 155.2, "timestamp_ms": 3000}
      {"type": "event", "event_type": "CHARGE", "timestamp_ms": 5000}
      {"type": "state", "state": "recording"}

    Client → Server messages:
      {"type": "control", "channel": "burner", "value": 0.8}
      {"type": "command", "action": "start_recording"}
    """
    await websocket.accept()
    try:
        while True:
            # Placeholder: echo received messages
            data = await websocket.receive_json()
            await websocket.send_json({"type": "ack", "received": data})
    except WebSocketDisconnect:
        pass
