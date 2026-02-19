"""Driver factory — creates the correct driver for a machine configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from openroast.drivers.modbus import ModbusDriver
from openroast.models.catalog import ProtocolType

if TYPE_CHECKING:
    from openroast.drivers.base import BaseDriver
    from openroast.models.machine import SavedMachine


def create_driver(machine: SavedMachine) -> BaseDriver:
    """Create the appropriate driver for a saved machine configuration.

    Args:
        machine: Machine configuration with protocol and connection details.

    Returns:
        An instance of the correct driver subclass.

    Raises:
        NotImplementedError: If the protocol is not yet supported.
    """
    match machine.protocol:
        case ProtocolType.MODBUS_RTU | ProtocolType.MODBUS_TCP:
            return ModbusDriver(machine)
        case ProtocolType.S7:
            raise NotImplementedError("S7 driver not yet implemented")
        case ProtocolType.SERIAL:
            raise NotImplementedError("Serial driver not yet implemented")
        case _:
            raise NotImplementedError(f"Unknown protocol: {machine.protocol}")
