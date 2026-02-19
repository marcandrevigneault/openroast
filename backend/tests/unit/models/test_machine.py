"""Unit tests for SavedMachine model."""

from __future__ import annotations

from openroast.models.catalog import (
    ChannelConfig,
    ControlConfig,
    ModbusConnectionConfig,
    ModbusRegisterConfig,
    ProtocolType,
    S7ConnectionConfig,
    SerialConnectionConfig,
)
from openroast.models.machine import SavedMachine


class TestSavedMachine:
    def test_auto_generates_id(self) -> None:
        m = SavedMachine(
            name="Test",
            protocol=ProtocolType.MODBUS_TCP,
            connection=ModbusConnectionConfig(),
        )
        assert m.id != ""
        assert len(m.id) > 0

    def test_explicit_id(self) -> None:
        m = SavedMachine(
            id="custom-id",
            name="Test",
            protocol=ProtocolType.SERIAL,
            connection=SerialConnectionConfig(),
        )
        assert m.id == "custom-id"

    def test_catalog_reference(self) -> None:
        m = SavedMachine(
            name="Stratto 2.0",
            catalog_manufacturer_id="carmomaq",
            catalog_model_id="carmomaq-stratto-2.0",
            protocol=ProtocolType.MODBUS_TCP,
            connection=ModbusConnectionConfig(host="192.168.5.11"),
        )
        assert m.catalog_manufacturer_id == "carmomaq"
        assert m.catalog_model_id == "carmomaq-stratto-2.0"

    def test_custom_machine_no_catalog(self) -> None:
        m = SavedMachine(
            name="My Custom Roaster",
            protocol=ProtocolType.MODBUS_RTU,
            connection=ModbusConnectionConfig(type="modbus_rtu"),
        )
        assert m.catalog_manufacturer_id is None
        assert m.catalog_model_id is None

    def test_with_channels_and_controls(self) -> None:
        m = SavedMachine(
            name="Full Config",
            protocol=ProtocolType.MODBUS_TCP,
            connection=ModbusConnectionConfig(),
            et=ChannelConfig(name="ET", modbus=ModbusRegisterConfig(address=43)),
            bt=ChannelConfig(name="BT", modbus=ModbusRegisterConfig(address=44)),
            controls=[
                ControlConfig(name="Burner", channel="burner", min=0, max=120),
            ],
        )
        assert m.et is not None
        assert m.et.modbus is not None
        assert m.et.modbus.address == 43
        assert len(m.controls) == 1

    def test_serialization_roundtrip(self) -> None:
        m = SavedMachine(
            name="Roundtrip",
            protocol=ProtocolType.S7,
            connection=S7ConnectionConfig(host="10.0.0.1"),
            sampling_interval_ms=2000,
        )
        data = m.model_dump()
        m2 = SavedMachine.model_validate(data)
        assert m2.name == "Roundtrip"
        assert m2.protocol == ProtocolType.S7
        assert m2.connection.type == "s7"
        assert m2.sampling_interval_ms == 2000

    def test_json_roundtrip(self) -> None:
        m = SavedMachine(
            name="JSON Test",
            protocol=ProtocolType.MODBUS_TCP,
            connection=ModbusConnectionConfig(),
        )
        json_str = m.model_dump_json()
        m2 = SavedMachine.model_validate_json(json_str)
        assert m2.name == m.name
        assert m2.id == m.id
