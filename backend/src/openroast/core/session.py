"""Roast session management.

A RoastSession tracks the lifecycle of a single roast from monitoring
through recording to completion. It accumulates temperature data,
detects events, and produces a RoastProfile when finished.
"""

from __future__ import annotations

from enum import Enum

from openroast.models.profile import RoastEvent, RoastProfile, TemperaturePoint


class SessionState(Enum):
    """Roast session lifecycle states."""

    IDLE = "idle"             # created but not started
    MONITORING = "monitoring"  # reading temps, not recording
    RECORDING = "recording"    # actively recording a roast
    FINISHED = "finished"      # roast complete, profile available


class RoastSession:
    """Manages the lifecycle of a single roast.

    State machine: IDLE → MONITORING → RECORDING → FINISHED
    """

    __slots__ = ["_controls", "_data", "_events", "_machine_name", "_state"]

    def __init__(self, machine_name: str = "") -> None:
        self._state = SessionState.IDLE
        self._data: list[TemperaturePoint] = []
        self._events: list[RoastEvent] = []
        self._controls: dict[str, list[tuple[float, float]]] = {}
        self._machine_name = machine_name

    @property
    def state(self) -> SessionState:
        """Current session state."""
        return self._state

    @property
    def data_points(self) -> int:
        """Number of recorded temperature points."""
        return len(self._data)

    def start_monitoring(self) -> None:
        """Begin monitoring (reading temps without recording)."""
        if self._state not in (SessionState.IDLE, SessionState.FINISHED):
            msg = f"Cannot start monitoring from {self._state.value}"
            raise ValueError(msg)
        self._state = SessionState.MONITORING

    def start_recording(self) -> None:
        """Begin recording a roast."""
        if self._state != SessionState.MONITORING:
            msg = f"Cannot start recording from {self._state.value}"
            raise ValueError(msg)
        self._state = SessionState.RECORDING
        self._data.clear()
        self._events.clear()
        self._controls.clear()

    def stop_monitoring(self) -> None:
        """Stop monitoring and return to idle."""
        if self._state != SessionState.MONITORING:
            msg = f"Cannot stop monitoring from {self._state.value}"
            raise ValueError(msg)
        self._state = SessionState.IDLE

    def stop_recording(self) -> None:
        """Stop recording and finalize the roast."""
        if self._state != SessionState.RECORDING:
            msg = f"Cannot stop recording from {self._state.value}"
            raise ValueError(msg)
        self._state = SessionState.FINISHED

    def add_reading(self, timestamp_ms: float, et: float, bt: float) -> None:
        """Add a temperature reading to the session.

        Only records data when in RECORDING state. In MONITORING state,
        readings are accepted but not stored (used for live display only).

        Args:
            timestamp_ms: Milliseconds since recording started.
            et: Environment temperature (Celsius).
            bt: Bean temperature (Celsius).
        """
        if self._state == SessionState.RECORDING:
            self._data.append(TemperaturePoint(timestamp_ms=timestamp_ms, et=et, bt=bt))

    def add_control_change(self, timestamp_ms: float, channel: str,
                           value: float) -> None:
        """Record a control value change during the session.

        Control changes are recorded in any active state (MONITORING or
        RECORDING) so pre-heat adjustments are captured.

        Args:
            timestamp_ms: When the control was changed.
            channel: Control channel name (e.g. 'burner', 'airflow').
            value: New control value.
        """
        if self._state in (SessionState.MONITORING, SessionState.RECORDING):
            if channel not in self._controls:
                self._controls[channel] = []
            self._controls[channel].append((timestamp_ms, value))

    def add_event(self, event_type: str, timestamp_ms: float,
                  auto_detected: bool = False) -> None:
        """Record a roast event (CHARGE, DRY, FCs, DROP, etc.).

        Args:
            event_type: Event identifier string.
            timestamp_ms: When the event occurred.
            auto_detected: Whether the event was auto-detected.
        """
        if self._state != SessionState.RECORDING:
            msg = f"Cannot add events in {self._state.value} state"
            raise ValueError(msg)
        self._events.append(RoastEvent(
            event_type=event_type,
            timestamp_ms=timestamp_ms,
            auto_detected=auto_detected,
        ))

    def to_profile(self, name: str = "Untitled") -> RoastProfile:
        """Export the recorded session as a RoastProfile.

        Returns:
            RoastProfile with all recorded data and events.

        Raises:
            ValueError: If the session has no recorded data.
        """
        if not self._data:
            msg = "No data recorded — cannot create profile"
            raise ValueError(msg)
        return RoastProfile(
            name=name,
            machine=self._machine_name,
            temperatures=list(self._data),
            events=list(self._events),
            controls={ch: list(pts) for ch, pts in self._controls.items()},
        )
