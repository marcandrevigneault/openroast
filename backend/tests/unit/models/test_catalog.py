"""Unit tests for catalog Pydantic models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from openroast.models.catalog import (
    CatalogManufacturer,
    CatalogModel,
    ChannelConfig,
    ControlConfig,
    MachineCatalog,
    ModbusConnectionConfig,
    ModbusRegisterConfig,
    ProtocolType,
    S7ConnectionConfig,
    S7RegisterConfig,
    SerialConnectionConfig,
)


class TestProtocolType:
    def test_values(self) -> None:
        assert ProtocolType.MODBUS_RTU == "modbus_rtu"
        assert ProtocolType.MODBUS_TCP == "modbus_tcp"
        assert ProtocolType.SERIAL == "serial"
        assert ProtocolType.S7 == "s7"


class TestModbusConnectionConfig:
    def test_defaults(self) -> None:
        c = ModbusConnectionConfig()
        assert c.type == "modbus_tcp"
        assert c.host == "192.168.1.1"
        assert c.port == 502
        assert c.baudrate == 19200
        assert c.parity == "N"
        assert c.word_order_little is True

    def test_rtu_type(self) -> None:
        c = ModbusConnectionConfig(type="modbus_rtu", host="/dev/ttyUSB0")
        assert c.type == "modbus_rtu"

    def test_invalid_port(self) -> None:
        with pytest.raises(ValidationError):
            ModbusConnectionConfig(port=0)

    def test_invalid_timeout(self) -> None:
        with pytest.raises(ValidationError):
            ModbusConnectionConfig(timeout=0)


class TestSerialConnectionConfig:
    def test_defaults(self) -> None:
        c = SerialConnectionConfig()
        assert c.type == "serial"
        assert c.comport == "/dev/ttyUSB0"
        assert c.baudrate == 115200

    def test_custom_values(self) -> None:
        c = SerialConnectionConfig(comport="/dev/cu.usbserial-1234", baudrate=57600)
        assert c.baudrate == 57600


class TestS7ConnectionConfig:
    def test_defaults(self) -> None:
        c = S7ConnectionConfig()
        assert c.type == "s7"
        assert c.port == 102
        assert c.rack == 0
        assert c.slot == 0


class TestModbusRegisterConfig:
    def test_defaults(self) -> None:
        r = ModbusRegisterConfig(address=43)
        assert r.code == 3
        assert r.device_id == 1
        assert r.divisor == 0
        assert r.mode == "C"
        assert r.is_float is False
        assert r.is_bcd is False

    def test_negative_register_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ModbusRegisterConfig(address=-1)


class TestS7RegisterConfig:
    def test_defaults(self) -> None:
        r = S7RegisterConfig(start=38)
        assert r.area == 6
        assert r.db_nr == 2
        assert r.type == 0
        assert r.mode == 1


class TestChannelConfig:
    def test_modbus_channel(self) -> None:
        ch = ChannelConfig(
            name="ET",
            modbus=ModbusRegisterConfig(address=43),
        )
        assert ch.modbus is not None
        assert ch.s7 is None

    def test_s7_channel(self) -> None:
        ch = ChannelConfig(
            name="BT",
            s7=S7RegisterConfig(start=36),
        )
        assert ch.s7 is not None
        assert ch.modbus is None


class TestControlConfig:
    def test_defaults(self) -> None:
        c = ControlConfig(name="Burner", channel="burner")
        assert c.min == 0
        assert c.max == 100
        assert c.step == 1
        assert c.unit == ""

    def test_custom_range(self) -> None:
        c = ControlConfig(name="Gas", channel="gas", min=80, max=350, unit="Pa")
        assert c.min == 80
        assert c.max == 350
        assert c.unit == "Pa"


class TestCatalogModel:
    def test_modbus_model(self) -> None:
        m = CatalogModel(
            id="test-modbus",
            name="Test MODBUS",
            protocol=ProtocolType.MODBUS_TCP,
            connection=ModbusConnectionConfig(),
        )
        assert m.protocol == "modbus_tcp"
        assert m.sampling_interval_ms == 3000

    def test_s7_model(self) -> None:
        m = CatalogModel(
            id="test-s7",
            name="Test S7",
            protocol=ProtocolType.S7,
            connection=S7ConnectionConfig(),
        )
        assert m.connection.type == "s7"

    def test_discriminated_union_roundtrip(self) -> None:
        m = CatalogModel(
            id="test",
            name="Test",
            protocol=ProtocolType.MODBUS_TCP,
            connection=ModbusConnectionConfig(host="10.0.0.1"),
            et=ChannelConfig(name="ET", modbus=ModbusRegisterConfig(address=43)),
            controls=[ControlConfig(name="Burner", channel="burner")],
        )
        data = m.model_dump()
        m2 = CatalogModel.model_validate(data)
        assert m2.connection.type == "modbus_tcp"
        assert m2.connection.host == "10.0.0.1"  # type: ignore[union-attr]
        assert m2.et is not None
        assert m2.et.modbus is not None
        assert m2.et.modbus.address == 43
        assert len(m2.controls) == 1


class TestCatalogManufacturer:
    def test_with_models(self) -> None:
        mfr = CatalogManufacturer(
            id="test-mfr",
            name="Test Manufacturer",
            country="US",
            models=[
                CatalogModel(
                    id="m1",
                    name="Model 1",
                    protocol=ProtocolType.SERIAL,
                    connection=SerialConnectionConfig(),
                ),
            ],
        )
        assert len(mfr.models) == 1
        assert mfr.country == "US"


class TestMachineCatalog:
    def test_empty_catalog(self) -> None:
        c = MachineCatalog()
        assert c.version == 1
        assert c.manufacturers == []

    def test_serialization_roundtrip(self) -> None:
        catalog = MachineCatalog(
            manufacturers=[
                CatalogManufacturer(
                    id="mfr1",
                    name="Mfr 1",
                    models=[
                        CatalogModel(
                            id="model1",
                            name="Model 1",
                            protocol=ProtocolType.MODBUS_TCP,
                            connection=ModbusConnectionConfig(),
                        ),
                    ],
                ),
            ],
        )
        data = catalog.model_dump()
        c2 = MachineCatalog.model_validate(data)
        assert len(c2.manufacturers) == 1
        assert c2.manufacturers[0].models[0].connection.type == "modbus_tcp"
