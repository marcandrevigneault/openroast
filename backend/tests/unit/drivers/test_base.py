"""Unit tests for the base driver protocol."""

from __future__ import annotations

import pytest

from openroast.drivers.base import (
    BaseDriver,
    ConnectionState,
    DriverInfo,
    TemperatureReading,
)


class TestTemperatureReading:
    def test_immutable(self) -> None:
        r = TemperatureReading(et=210.0, bt=155.0, timestamp_ms=3000.0)
        with pytest.raises(AttributeError):
            r.et = 999.0  # type: ignore[misc]

    def test_fields(self) -> None:
        r = TemperatureReading(et=210.5, bt=155.2, timestamp_ms=3000.0)
        assert r.et == 210.5
        assert r.bt == 155.2
        assert r.timestamp_ms == 3000.0


class TestDriverInfo:
    def test_immutable(self) -> None:
        info = DriverInfo(name="Test", manufacturer="Acme", model="X1", protocol="serial")
        with pytest.raises(AttributeError):
            info.name = "changed"  # type: ignore[misc]

    def test_fields(self) -> None:
        info = DriverInfo(name="Modbus RTU", manufacturer="Carmomaq",
                          model="Stratto", protocol="modbus_rtu")
        assert info.manufacturer == "Carmomaq"
        assert info.protocol == "modbus_rtu"


class TestConnectionState:
    def test_all_states_exist(self) -> None:
        assert ConnectionState.DISCONNECTED.value == "disconnected"
        assert ConnectionState.CONNECTING.value == "connecting"
        assert ConnectionState.CONNECTED.value == "connected"
        assert ConnectionState.ERROR.value == "error"


class TestBaseDriverProtocol:
    """Verify that BaseDriver enforces the interface contract."""

    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            BaseDriver()  # type: ignore[abstract]

    async def test_write_control_default_raises(self) -> None:
        """Default write_control raises NotImplementedError."""

        class MinimalDriver(BaseDriver):
            async def connect(self) -> None: pass
            async def disconnect(self) -> None: pass
            async def read_temperatures(self) -> TemperatureReading:
                return TemperatureReading(et=0, bt=0, timestamp_ms=0)
            def info(self) -> DriverInfo:
                return DriverInfo("t", "t", "t", "t")
            @property
            def state(self) -> ConnectionState:
                return ConnectionState.DISCONNECTED

        driver = MinimalDriver()
        with pytest.raises(NotImplementedError):
            await driver.write_control("burner", 0.5)

    async def test_read_extra_channels_default_empty(self) -> None:
        """Default read_extra_channels returns empty dict."""

        class MinimalDriver(BaseDriver):
            async def connect(self) -> None: pass
            async def disconnect(self) -> None: pass
            async def read_temperatures(self) -> TemperatureReading:
                return TemperatureReading(et=0, bt=0, timestamp_ms=0)
            def info(self) -> DriverInfo:
                return DriverInfo("t", "t", "t", "t")
            @property
            def state(self) -> ConnectionState:
                return ConnectionState.DISCONNECTED

        driver = MinimalDriver()
        result = await driver.read_extra_channels()
        assert result == {}
