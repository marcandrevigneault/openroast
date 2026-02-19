"""Abstract base driver for roaster communication.

All machine drivers implement this protocol. The driver abstraction allows
the rest of the system to work with any roaster without knowing the
communication details (Modbus RTU, serial, TCP, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class ConnectionState(Enum):
    """Driver connection state."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass(frozen=True)
class TemperatureReading:
    """A single temperature reading from the roaster.

    Attributes:
        et: Environment/exhaust temperature in Celsius.
        bt: Bean temperature in Celsius.
        timestamp_ms: Milliseconds since roast start (0 during monitoring).
    """

    et: float
    bt: float
    timestamp_ms: float


@dataclass(frozen=True)
class DriverInfo:
    """Metadata about a driver implementation.

    Attributes:
        name: Human-readable driver name (e.g., "Modbus RTU").
        manufacturer: Roaster manufacturer (e.g., "Carmomaq").
        model: Roaster model (e.g., "Stratto 2.0").
        protocol: Communication protocol identifier.
    """

    name: str
    manufacturer: str
    model: str
    protocol: str


class BaseDriver(ABC):
    """Abstract base class for all roaster drivers.

    Subclasses must implement connect/disconnect/read_temperatures
    and optionally write_control for machines that support it.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the roaster hardware."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the roaster hardware."""

    @abstractmethod
    async def read_temperatures(self) -> TemperatureReading:
        """Read current ET and BT from the roaster.

        Returns:
            TemperatureReading with current values.

        Raises:
            ConnectionError: If not connected or communication fails.
        """

    @abstractmethod
    def info(self) -> DriverInfo:
        """Return metadata about this driver."""

    @property
    @abstractmethod
    def state(self) -> ConnectionState:
        """Current connection state."""

    async def write_control(self, channel: str, value: float) -> None:
        """Write a control value to the roaster (optional).

        Args:
            channel: Control channel name (e.g., "burner", "airflow", "fan").
            value: Normalized value 0.0-1.0.

        Raises:
            NotImplementedError: If the driver does not support control output.
        """
        raise NotImplementedError(f"{self.info().name} does not support control output")

    async def read_extra_channels(self) -> dict[str, float]:
        """Read extra sensor channels beyond ET/BT (optional).

        Returns:
            Dict mapping channel names to values.
        """
        return {}
