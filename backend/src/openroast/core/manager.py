"""Machine manager — orchestrates driver instances, sampling loops, and WebSocket fan-out.

The MachineManager is the central runtime component. It ties together
SavedMachine configs, BaseDriver instances, RoastSessions, and WebSocket
clients into a coherent real-time data pipeline.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from openroast.core.session import RoastSession
from openroast.drivers.factory import create_driver
from openroast.models.ws_messages import (
    CommandAction,
    ConnectionMessage,
    ControlAckMessage,
    DriverStateValue,
    ErrorMessage,
    SessionStateValue,
    StateMessage,
    TemperatureMessage,
)

if TYPE_CHECKING:
    from fastapi import WebSocket

    from openroast.core.machine_storage import MachineStorage
    from openroast.drivers.base import BaseDriver
    from openroast.models.catalog import ControlConfig
    from openroast.models.machine import SavedMachine
    from openroast.models.ws_messages import ServerMessage

logger = logging.getLogger(__name__)

# Maximum number of temperature messages to buffer for reconnect sync.
_RING_BUFFER_SIZE = 120  # ~60s at 500ms sampling


@dataclass
class MachineInstance:
    """Runtime state for a single connected machine."""

    machine: SavedMachine
    driver: BaseDriver
    session: RoastSession
    subscribers: set[WebSocket] = field(default_factory=set)
    sampling_task: asyncio.Task[None] | None = None
    ring_buffer: deque[TemperatureMessage] = field(
        default_factory=lambda: deque(maxlen=_RING_BUFFER_SIZE)
    )
    prev_et: float | None = None
    prev_bt: float | None = None
    start_time_ms: float = 0.0
    consecutive_errors: int = 0
    control_enabled: dict[str, bool] = field(default_factory=dict)


class MachineManager:
    """Manages active driver instances, sampling loops, and WebSocket fan-out.

    Args:
        machine_storage: Storage backend for loading machine configurations.
    """

    _MAX_CONSECUTIVE_ERRORS = 5

    def __init__(self, machine_storage: MachineStorage) -> None:
        self._storage = machine_storage
        self._instances: dict[str, MachineInstance] = {}

    @property
    def active_machines(self) -> list[str]:
        """List IDs of all currently connected machines."""
        return list(self._instances.keys())

    def get_instance(self, machine_id: str) -> MachineInstance | None:
        """Get the runtime instance for a connected machine."""
        return self._instances.get(machine_id)

    async def connect_machine(self, machine_id: str) -> None:
        """Load a machine config, create a driver, connect, and start sampling.

        Args:
            machine_id: ID of the saved machine to connect.

        Raises:
            ValueError: If machine not found in storage.
            ConnectionError: If driver fails to connect.
        """
        if machine_id in self._instances:
            return  # Already connected

        machine = self._storage.get(machine_id)
        if machine is None:
            msg = f"Machine '{machine_id}' not found in storage"
            raise ValueError(msg)

        driver = create_driver(machine)
        await driver.connect()

        instance = MachineInstance(
            machine=machine,
            driver=driver,
            session=RoastSession(machine_name=machine.name),
            start_time_ms=time.monotonic() * 1000,
        )
        self._instances[machine_id] = instance

        # Start the sampling loop
        instance.sampling_task = asyncio.create_task(
            self._sampling_loop(machine_id),
            name=f"sampling-{machine_id}",
        )

        logger.info("Connected machine %s (%s)", machine.name, machine_id)

    async def disconnect_machine(self, machine_id: str) -> None:
        """Stop sampling, disconnect driver, and clean up.

        Args:
            machine_id: ID of the machine to disconnect.
        """
        instance = self._instances.pop(machine_id, None)
        if instance is None:
            return

        # Cancel sampling loop
        if instance.sampling_task and not instance.sampling_task.done():
            instance.sampling_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await instance.sampling_task

        # Disconnect driver
        try:
            await instance.driver.disconnect()
        except Exception:
            logger.exception("Error disconnecting machine %s", machine_id)

        # Notify subscribers
        msg = ConnectionMessage(
            driver_state=DriverStateValue.DISCONNECTED,
            driver_name=instance.driver.info().name,
            message="Disconnected",
        )
        await self._broadcast(instance, msg)

        logger.info("Disconnected machine %s", machine_id)

    async def subscribe(self, machine_id: str, ws: WebSocket) -> None:
        """Register a WebSocket client to receive broadcasts for a machine."""
        instance = self._instances.get(machine_id)
        if instance:
            instance.subscribers.add(ws)

    async def unsubscribe(self, machine_id: str, ws: WebSocket) -> None:
        """Remove a WebSocket client from a machine's subscriber list."""
        instance = self._instances.get(machine_id)
        if instance:
            instance.subscribers.discard(ws)

    async def handle_control(
        self,
        machine_id: str,
        channel: str,
        value_normalized: float,
        *,
        enabled: bool = True,
    ) -> ControlAckMessage:
        """Handle a control command from a WebSocket client.

        Scales the normalized 0-1 value to the control's native range and
        forwards it to the driver.  When *enabled* is False the driver
        receives 0 regardless of the requested value.

        Args:
            machine_id: Target machine.
            channel: Control channel name.
            value_normalized: Value in 0.0-1.0 range.
            enabled: Whether the control is active.

        Returns:
            ControlAckMessage indicating success or failure.
        """
        instance = self._instances.get(machine_id)
        if instance is None:
            return ControlAckMessage(
                channel=channel, value=value_normalized,
                applied=False, enabled=enabled,
                message="Machine not connected",
            )

        control = self._find_control(instance.machine, channel)
        if control is None:
            return ControlAckMessage(
                channel=channel, value=value_normalized,
                applied=False, enabled=enabled,
                message=f"Unknown control channel: {channel}",
            )

        instance.control_enabled[channel] = enabled
        write_value = value_normalized if enabled else 0.0
        native_value = self._scale_to_native(control, write_value)

        try:
            await instance.driver.write_control(channel, native_value)

            # Record the control change in the session
            elapsed_ms = time.monotonic() * 1000 - instance.start_time_ms
            instance.session.add_control_change(elapsed_ms, channel, native_value)

            return ControlAckMessage(
                channel=channel, value=value_normalized,
                applied=True, enabled=enabled,
            )
        except (ConnectionError, NotImplementedError) as e:
            return ControlAckMessage(
                channel=channel, value=value_normalized,
                applied=False, enabled=enabled, message=str(e),
            )

    async def handle_session_command(
        self,
        machine_id: str,
        action: CommandAction,
        event_type: str | None = None,
    ) -> StateMessage | ErrorMessage:
        """Handle a session lifecycle command.

        Args:
            machine_id: Target machine.
            action: The session action to perform.
            event_type: Required for mark_event action.

        Returns:
            StateMessage on success, ErrorMessage on failure.
        """
        instance = self._instances.get(machine_id)
        if instance is None:
            return ErrorMessage(
                code="MACHINE_NOT_FOUND",
                message=f"Machine '{machine_id}' not connected",
                recoverable=False,
            )

        session = instance.session
        prev_state = SessionStateValue(session.state.value)

        try:
            if action == CommandAction.START_MONITORING:
                session.start_monitoring()
                # Reset clock so chart starts at t=0
                instance.start_time_ms = time.monotonic() * 1000
                instance.prev_et = None
                instance.prev_bt = None
            elif action == CommandAction.STOP_MONITORING:
                session.stop_monitoring()
            elif action == CommandAction.START_RECORDING:
                session.start_recording()
                # Reset clock so the recording chart starts at t=0
                instance.start_time_ms = time.monotonic() * 1000
                instance.prev_et = None
                instance.prev_bt = None
            elif action == CommandAction.STOP_RECORDING:
                session.stop_recording()
            elif action == CommandAction.MARK_EVENT:
                if event_type is None:
                    return ErrorMessage(
                        code="INVALID_MESSAGE",
                        message="event_type required for mark_event",
                    )
                elapsed_ms = time.monotonic() * 1000 - instance.start_time_ms
                session.add_event(event_type, elapsed_ms)
                # Return a state message (state doesn't change for events)
                return StateMessage(state=prev_state, previous_state=prev_state)
            elif action == CommandAction.RESET:
                instance.session = RoastSession(machine_name=instance.machine.name)
                instance.start_time_ms = time.monotonic() * 1000
                return StateMessage(
                    state=SessionStateValue.IDLE,
                    previous_state=prev_state,
                )
            else:
                return ErrorMessage(
                    code="INVALID_MESSAGE",
                    message=f"Unknown action: {action}",
                )
        except ValueError as e:
            return ErrorMessage(
                code="INVALID_STATE_TRANSITION",
                message=str(e),
            )

        new_state = SessionStateValue(session.state.value)
        return StateMessage(state=new_state, previous_state=prev_state)

    def get_sync_messages(
        self, machine_id: str, since_ms: float
    ) -> list[TemperatureMessage]:
        """Get buffered temperature messages since a given timestamp.

        Used for reconnect sync — replays missed data to a reconnecting client.

        Args:
            machine_id: Target machine.
            since_ms: Replay messages with timestamp > this value.

        Returns:
            List of temperature messages since the given timestamp.
        """
        instance = self._instances.get(machine_id)
        if instance is None:
            return []

        return [
            msg for msg in instance.ring_buffer
            if msg.timestamp_ms > since_ms
        ]

    # ── Internal helpers ──────────────────────────────────────────────

    async def _sampling_loop(self, machine_id: str) -> None:
        """Read temperatures at the configured interval and broadcast.

        Runs until cancelled or the machine is disconnected.
        """
        instance = self._instances.get(machine_id)
        if instance is None:
            return

        interval_s = instance.machine.sampling_interval_ms / 1000.0

        while True:
            try:
                reading = await instance.driver.read_temperatures()
                extra = await instance.driver.read_extra_channels()

                elapsed_ms = time.monotonic() * 1000 - instance.start_time_ms

                # Compute rate of rise (°C per minute)
                et_ror = self._compute_ror(
                    reading.et, instance.prev_et, interval_s,
                )
                bt_ror = self._compute_ror(
                    reading.bt, instance.prev_bt, interval_s,
                )
                instance.prev_et = reading.et
                instance.prev_bt = reading.bt

                # Create temperature message
                temp_msg = TemperatureMessage(
                    timestamp_ms=elapsed_ms,
                    et=reading.et,
                    bt=reading.bt,
                    et_ror=et_ror,
                    bt_ror=bt_ror,
                    extra_channels=extra,
                )

                # Feed session
                instance.session.add_reading(elapsed_ms, reading.et, reading.bt)

                # Buffer for reconnect sync
                instance.ring_buffer.append(temp_msg)

                # Broadcast to subscribers
                await self._broadcast(instance, temp_msg)

                # Reset error counter on success
                instance.consecutive_errors = 0

            except asyncio.CancelledError:
                raise
            except ConnectionError as e:
                instance.consecutive_errors += 1
                logger.warning(
                    "Read error on %s (%d/%d): %s",
                    machine_id,
                    instance.consecutive_errors,
                    self._MAX_CONSECUTIVE_ERRORS,
                    e,
                )

                if instance.consecutive_errors >= self._MAX_CONSECUTIVE_ERRORS:
                    error_msg = ConnectionMessage(
                        driver_state=DriverStateValue.ERROR,
                        driver_name=instance.driver.info().name,
                        message=f"Lost connection after {self._MAX_CONSECUTIVE_ERRORS} errors",
                    )
                    await self._broadcast(instance, error_msg)
                    return  # Stop sampling

                err_msg = ErrorMessage(
                    code="DRIVER_READ_FAILED",
                    message=str(e),
                    recoverable=True,
                )
                await self._broadcast(instance, err_msg)

            except Exception:
                logger.exception("Unexpected error in sampling loop for %s", machine_id)
                return

            await asyncio.sleep(interval_s)

    @staticmethod
    async def _broadcast(instance: MachineInstance, message: ServerMessage) -> None:
        """Send a message to all WebSocket subscribers of a machine."""
        data = message.model_dump()
        dead: list[WebSocket] = []

        for ws in instance.subscribers:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)

        for ws in dead:
            instance.subscribers.discard(ws)

    @staticmethod
    def _compute_ror(
        current: float,
        previous: float | None,
        interval_s: float,
    ) -> float:
        """Compute rate of rise in °C per minute.

        Args:
            current: Current temperature reading.
            previous: Previous temperature reading (None on first read).
            interval_s: Sampling interval in seconds.

        Returns:
            Rate of rise in °C/min, or 0.0 if previous is None.
        """
        if previous is None or interval_s <= 0:
            return 0.0
        return (current - previous) / (interval_s / 60.0)

    @staticmethod
    def _find_control(
        machine: SavedMachine, channel: str
    ) -> ControlConfig | None:
        """Find a ControlConfig by channel name."""
        for c in machine.controls:
            if c.channel == channel:
                return c
        return None

    @staticmethod
    def _scale_to_native(control: ControlConfig, normalized: float) -> float:
        """Scale a normalized 0-1 value to the control's native range.

        Args:
            control: Control configuration with min/max.
            normalized: Value in 0.0-1.0 range.

        Returns:
            Value in the control's native range [min, max].
        """
        return control.min + normalized * (control.max - control.min)
