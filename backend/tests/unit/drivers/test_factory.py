"""Unit tests for the driver factory."""

from __future__ import annotations

import pytest

from openroast.drivers.factory import create_driver
from openroast.drivers.modbus import ModbusDriver
from openroast.models.catalog import (
    ModbusConnectionConfig,
    ProtocolType,
    S7ConnectionConfig,
    SerialConnectionConfig,
)
from openroast.models.machine import SavedMachine


def _make_machine(protocol: ProtocolType, **conn_kwargs: object) -> SavedMachine:
    """Create a minimal SavedMachine for factory testing."""
    if protocol in (ProtocolType.MODBUS_RTU, ProtocolType.MODBUS_TCP):
        conn_type = "modbus_tcp" if protocol == ProtocolType.MODBUS_TCP else "modbus_rtu"
        connection = ModbusConnectionConfig(type=conn_type, **conn_kwargs)
    elif protocol == ProtocolType.SERIAL:
        connection = SerialConnectionConfig(**conn_kwargs)
    elif protocol == ProtocolType.S7:
        connection = S7ConnectionConfig(**conn_kwargs)
    else:
        msg = f"Unknown protocol: {protocol}"
        raise ValueError(msg)

    return SavedMachine(
        id="factory-test",
        name="Factory Test Machine",
        protocol=protocol,
        connection=connection,
    )


class TestCreateDriver:
    def test_modbus_tcp_creates_modbus_driver(self) -> None:
        machine = _make_machine(ProtocolType.MODBUS_TCP)
        driver = create_driver(machine)
        assert isinstance(driver, ModbusDriver)

    def test_modbus_rtu_creates_modbus_driver(self) -> None:
        machine = _make_machine(ProtocolType.MODBUS_RTU, host="/dev/ttyUSB0")
        driver = create_driver(machine)
        assert isinstance(driver, ModbusDriver)

    def test_s7_raises_not_implemented(self) -> None:
        machine = _make_machine(ProtocolType.S7)
        with pytest.raises(NotImplementedError, match="S7"):
            create_driver(machine)

    def test_serial_raises_not_implemented(self) -> None:
        machine = _make_machine(ProtocolType.SERIAL)
        with pytest.raises(NotImplementedError, match="Serial"):
            create_driver(machine)
