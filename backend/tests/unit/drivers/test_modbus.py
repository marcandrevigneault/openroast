"""Unit tests for the Modbus RTU/TCP driver."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openroast.drivers.base import ConnectionState, TemperatureReading
from openroast.drivers.modbus import ModbusDriver, _bcd_to_int, _fahrenheit_to_celsius
from openroast.models.catalog import (
    ChannelConfig,
    ControlConfig,
    ModbusConnectionConfig,
    ModbusRegisterConfig,
    ProtocolType,
)
from openroast.models.machine import SavedMachine

# ── Fixtures ──────────────────────────────────────────────────────────


def _make_machine(
    protocol: ProtocolType = ProtocolType.MODBUS_TCP,
    et_address: int = 43,
    bt_address: int = 44,
    et_device_id: int = 1,
    bt_device_id: int = 1,
    divisor: int = 1,
    mode: str = "C",
    is_float: bool = False,
    is_bcd: bool = False,
    extra_channels: list[ChannelConfig] | None = None,
    controls: list[ControlConfig] | None = None,
    word_order_little: bool = True,
    host: str = "192.168.1.1",
    baudrate: int = 19200,
    stopbits: int = 1,
    parity: str = "N",
) -> SavedMachine:
    """Create a SavedMachine for testing."""
    conn_type = "modbus_tcp" if protocol == ProtocolType.MODBUS_TCP else "modbus_rtu"
    return SavedMachine(
        id="test-machine",
        name="Test Machine",
        protocol=protocol,
        connection=ModbusConnectionConfig(
            type=conn_type,
            host=host,
            port=502,
            baudrate=baudrate,
            bytesize=8,
            parity=parity,
            stopbits=stopbits,
            timeout=1.0,
            word_order_little=word_order_little,
        ),
        sampling_interval_ms=2000,
        et=ChannelConfig(
            name="ET",
            modbus=ModbusRegisterConfig(
                address=et_address,
                code=3,
                device_id=et_device_id,
                divisor=divisor,
                mode=mode,
                is_float=is_float,
                is_bcd=is_bcd,
            ),
        ),
        bt=ChannelConfig(
            name="BT",
            modbus=ModbusRegisterConfig(
                address=bt_address,
                code=3,
                device_id=bt_device_id,
                divisor=divisor,
                mode=mode,
                is_float=is_float,
                is_bcd=is_bcd,
            ),
        ),
        extra_channels=extra_channels or [],
        controls=controls or [],
    )


def _mock_response(registers: list[int], is_error: bool = False) -> MagicMock:
    """Create a mock Modbus register response."""
    resp = MagicMock()
    resp.registers = registers
    resp.isError.return_value = is_error
    return resp


@pytest.fixture
def tcp_machine() -> SavedMachine:
    return _make_machine(protocol=ProtocolType.MODBUS_TCP)


@pytest.fixture
def rtu_machine() -> SavedMachine:
    return _make_machine(
        protocol=ProtocolType.MODBUS_RTU,
        host="/dev/ttyUSB0",
        baudrate=115200,
        stopbits=2,
        parity="N",
    )


# ── Helper function tests ────────────────────────────────────────────


class TestBcdToInt:
    def test_zero(self) -> None:
        assert _bcd_to_int(0x0000) == 0

    def test_simple(self) -> None:
        assert _bcd_to_int(0x0215) == 215

    def test_round_number(self) -> None:
        assert _bcd_to_int(0x0400) == 400

    def test_max_four_digit(self) -> None:
        assert _bcd_to_int(0x9999) == 9999

    def test_single_digit(self) -> None:
        assert _bcd_to_int(0x0007) == 7


class TestFahrenheitToCelsius:
    def test_freezing(self) -> None:
        assert _fahrenheit_to_celsius(32.0) == pytest.approx(0.0)

    def test_boiling(self) -> None:
        assert _fahrenheit_to_celsius(212.0) == pytest.approx(100.0)

    def test_roast_temp(self) -> None:
        # 400°F ≈ 204.44°C
        assert _fahrenheit_to_celsius(400.0) == pytest.approx(204.444, rel=1e-2)


# ── Constructor tests ─────────────────────────────────────────────────


class TestModbusDriverInit:
    def test_tcp_machine(self, tcp_machine: SavedMachine) -> None:
        driver = ModbusDriver(tcp_machine)
        assert driver.state == ConnectionState.DISCONNECTED
        assert driver.info().protocol == "modbus_tcp"
        assert driver.info().name == "Modbus TCP"

    def test_rtu_machine(self, rtu_machine: SavedMachine) -> None:
        driver = ModbusDriver(rtu_machine)
        assert driver.info().protocol == "modbus_rtu"
        assert driver.info().name == "Modbus RTU"

    def test_rejects_serial_protocol(self) -> None:
        with pytest.raises(ValueError, match="modbus_rtu or modbus_tcp"):
            ModbusDriver(
                SavedMachine(
                    id="x",
                    name="X",
                    protocol=ProtocolType.SERIAL,
                    connection={"type": "serial", "comport": "/dev/ttyUSB0"},
                )
            )

    def test_builds_control_lookup(self) -> None:
        machine = _make_machine(controls=[
            ControlConfig(
                name="Gas", channel="gas", command="writeSingle(1,47,{})",
                min=0, max=100,
            ),
            ControlConfig(
                name="Air", channel="air", command="writeSingle(1,48,{})",
                min=0, max=120,
            ),
        ])
        driver = ModbusDriver(machine)
        assert "gas" in driver._controls
        assert "air" in driver._controls


# ── Connect / Disconnect tests ────────────────────────────────────────


class TestModbusDriverConnect:
    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_tcp_connect(self, mock_cls: MagicMock, tcp_machine: SavedMachine) -> None:
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_cls.return_value = mock_client

        driver = ModbusDriver(tcp_machine)
        await driver.connect()

        assert driver.state == ConnectionState.CONNECTED
        mock_cls.assert_called_once_with("192.168.1.1", port=502, timeout=1.0)
        mock_client.connect.assert_awaited_once()

    @patch("openroast.drivers.modbus.AsyncModbusSerialClient")
    async def test_rtu_connect(self, mock_cls: MagicMock, rtu_machine: SavedMachine) -> None:
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_cls.return_value = mock_client

        driver = ModbusDriver(rtu_machine)
        await driver.connect()

        assert driver.state == ConnectionState.CONNECTED
        mock_cls.assert_called_once_with(
            "/dev/ttyUSB0",
            baudrate=115200,
            bytesize=8,
            parity="N",
            stopbits=2,
            timeout=1.0,
        )

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_connect_failure_sets_error_state(
        self, mock_cls: MagicMock, tcp_machine: SavedMachine
    ) -> None:
        mock_client = AsyncMock()
        mock_client.connected = False
        mock_cls.return_value = mock_client

        driver = ModbusDriver(tcp_machine)
        with pytest.raises(ConnectionError, match="Failed to establish"):
            await driver.connect()

        assert driver.state == ConnectionState.ERROR

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_connect_idempotent_when_connected(
        self, mock_cls: MagicMock, tcp_machine: SavedMachine
    ) -> None:
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_cls.return_value = mock_client

        driver = ModbusDriver(tcp_machine)
        await driver.connect()
        await driver.connect()  # should be a no-op

        mock_client.connect.assert_awaited_once()

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_disconnect(self, mock_cls: MagicMock, tcp_machine: SavedMachine) -> None:
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_cls.return_value = mock_client

        driver = ModbusDriver(tcp_machine)
        await driver.connect()
        await driver.disconnect()

        assert driver.state == ConnectionState.DISCONNECTED
        mock_client.close.assert_called_once()


# ── Register reading tests ────────────────────────────────────────────


class TestReadRegister:
    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_read_holding_register_integer(self, mock_cls: MagicMock) -> None:
        """Read a simple 16-bit integer holding register."""
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_client.read_holding_registers = AsyncMock(return_value=_mock_response([2105]))
        mock_cls.return_value = mock_client

        machine = _make_machine(et_address=43, divisor=1, mode="C")
        driver = ModbusDriver(machine)
        await driver.connect()

        config = machine.et.modbus  # type: ignore[union-attr]
        value = await driver._read_register(config)
        assert value == pytest.approx(210.5)  # 2105 / 10

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_read_no_divisor(self, mock_cls: MagicMock) -> None:
        """divisor=0 means no division."""
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_client.read_holding_registers = AsyncMock(return_value=_mock_response([42]))
        mock_cls.return_value = mock_client

        machine = _make_machine(divisor=0, mode="C")
        driver = ModbusDriver(machine)
        await driver.connect()

        config = machine.et.modbus  # type: ignore[union-attr]
        value = await driver._read_register(config)
        assert value == pytest.approx(42.0)

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_read_divisor_2(self, mock_cls: MagicMock) -> None:
        """divisor=2 means divide by 100."""
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_client.read_holding_registers = AsyncMock(return_value=_mock_response([21050]))
        mock_cls.return_value = mock_client

        machine = _make_machine(divisor=2, mode="C")
        driver = ModbusDriver(machine)
        await driver.connect()

        config = machine.et.modbus  # type: ignore[union-attr]
        value = await driver._read_register(config)
        assert value == pytest.approx(210.5)  # 21050 / 100

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_read_input_register(self, mock_cls: MagicMock) -> None:
        """Function code 4 reads input registers."""
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_client.read_input_registers = AsyncMock(return_value=_mock_response([1550]))
        mock_cls.return_value = mock_client

        machine = _make_machine(divisor=1, mode="C")
        # Override ET to use code 4
        machine.et.modbus.code = 4  # type: ignore[union-attr]
        driver = ModbusDriver(machine)
        await driver.connect()

        config = machine.et.modbus  # type: ignore[union-attr]
        value = await driver._read_register(config)
        assert value == pytest.approx(155.0)

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_read_bcd_register(self, mock_cls: MagicMock) -> None:
        """BCD-encoded values (Loring machines)."""
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_client.read_holding_registers = AsyncMock(return_value=_mock_response([0x0400]))
        mock_cls.return_value = mock_client

        machine = _make_machine(is_bcd=True, divisor=0, mode="F")
        driver = ModbusDriver(machine)
        await driver.connect()

        config = machine.et.modbus  # type: ignore[union-attr]
        value = await driver._read_register(config)
        # BCD 0x0400 = 400, mode F → 400°F = 204.44°C
        assert value == pytest.approx(204.444, rel=1e-2)

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_read_float_register_little_endian(self, mock_cls: MagicMock) -> None:
        """32-bit IEEE 754 float with little-endian word order."""
        import struct

        # Encode 210.5 as IEEE 754 float
        packed = struct.pack(">f", 210.5)
        high, low = struct.unpack(">HH", packed)

        mock_client = AsyncMock()
        mock_client.connected = True
        # Little endian: [low, high]
        mock_client.read_holding_registers = AsyncMock(
            return_value=_mock_response([low, high])
        )
        mock_cls.return_value = mock_client

        machine = _make_machine(is_float=True, divisor=0, mode="C", word_order_little=True)
        driver = ModbusDriver(machine)
        await driver.connect()

        config = machine.et.modbus  # type: ignore[union-attr]
        value = await driver._read_register(config)
        assert value == pytest.approx(210.5)

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_read_float_register_big_endian(self, mock_cls: MagicMock) -> None:
        """32-bit IEEE 754 float with big-endian word order."""
        import struct

        packed = struct.pack(">f", 155.2)
        high, low = struct.unpack(">HH", packed)

        mock_client = AsyncMock()
        mock_client.connected = True
        # Big endian: [high, low]
        mock_client.read_holding_registers = AsyncMock(
            return_value=_mock_response([high, low])
        )
        mock_cls.return_value = mock_client

        machine = _make_machine(is_float=True, divisor=0, mode="C", word_order_little=False)
        driver = ModbusDriver(machine)
        await driver.connect()

        config = machine.et.modbus  # type: ignore[union-attr]
        value = await driver._read_register(config)
        assert value == pytest.approx(155.2, rel=1e-4)

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_read_signed_negative(self, mock_cls: MagicMock) -> None:
        """Negative signed 16-bit integer."""
        mock_client = AsyncMock()
        mock_client.connected = True
        # 0xFFFF = -1 as signed 16-bit
        mock_client.read_holding_registers = AsyncMock(return_value=_mock_response([0xFFFF]))
        mock_cls.return_value = mock_client

        machine = _make_machine(divisor=0, mode="")
        driver = ModbusDriver(machine)
        await driver.connect()

        config = machine.et.modbus  # type: ignore[union-attr]
        value = await driver._read_register(config)
        assert value == pytest.approx(-1.0)

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_read_fahrenheit_conversion(self, mock_cls: MagicMock) -> None:
        """Mode F converts Fahrenheit to Celsius."""
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_client.read_holding_registers = AsyncMock(return_value=_mock_response([4000]))
        mock_cls.return_value = mock_client

        machine = _make_machine(divisor=1, mode="F")
        driver = ModbusDriver(machine)
        await driver.connect()

        config = machine.et.modbus  # type: ignore[union-attr]
        value = await driver._read_register(config)
        # 4000 / 10 = 400°F → ≈ 204.44°C
        assert value == pytest.approx(204.444, rel=1e-2)

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_read_error_response(self, mock_cls: MagicMock) -> None:
        """Error response raises ConnectionError."""
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_client.read_holding_registers = AsyncMock(
            return_value=_mock_response([], is_error=True)
        )
        mock_cls.return_value = mock_client

        machine = _make_machine()
        driver = ModbusDriver(machine)
        await driver.connect()

        config = machine.et.modbus  # type: ignore[union-attr]
        with pytest.raises(ConnectionError, match="Modbus error response"):
            await driver._read_register(config)

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_read_connection_exception(self, mock_cls: MagicMock) -> None:
        """ConnectionException from pymodbus sets error state."""
        from pymodbus.exceptions import ConnectionException

        mock_client = AsyncMock()
        mock_client.connected = True
        mock_client.read_holding_registers = AsyncMock(
            side_effect=ConnectionException("timeout")
        )
        mock_cls.return_value = mock_client

        machine = _make_machine()
        driver = ModbusDriver(machine)
        await driver.connect()

        config = machine.et.modbus  # type: ignore[union-attr]
        with pytest.raises(ConnectionError, match="Modbus read failed"):
            await driver._read_register(config)

        assert driver.state == ConnectionState.ERROR


# ── read_temperatures tests ───────────────────────────────────────────


class TestReadTemperatures:
    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_read_et_and_bt(self, mock_cls: MagicMock) -> None:
        mock_client = AsyncMock()
        mock_client.connected = True
        # ET reads first, then BT
        mock_client.read_holding_registers = AsyncMock(
            side_effect=[_mock_response([2105]), _mock_response([1552])]
        )
        mock_cls.return_value = mock_client

        machine = _make_machine(et_address=43, bt_address=44, divisor=1, mode="C")
        driver = ModbusDriver(machine)
        await driver.connect()

        reading = await driver.read_temperatures()
        assert isinstance(reading, TemperatureReading)
        assert reading.et == pytest.approx(210.5)
        assert reading.bt == pytest.approx(155.2)
        assert reading.timestamp_ms == 0.0

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_read_with_different_device_ids(self, mock_cls: MagicMock) -> None:
        """Coffed uses different device_ids for ET/BT on same register."""
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_client.read_holding_registers = AsyncMock(
            side_effect=[_mock_response([210]), _mock_response([155])]
        )
        mock_cls.return_value = mock_client

        machine = _make_machine(
            et_address=52,
            bt_address=52,
            et_device_id=4,
            bt_device_id=3,
            divisor=0,
            mode="C",
        )
        driver = ModbusDriver(machine)
        await driver.connect()

        reading = await driver.read_temperatures()
        assert reading.et == pytest.approx(210.0)
        assert reading.bt == pytest.approx(155.0)

        # Verify device_id was passed correctly
        calls = mock_client.read_holding_registers.call_args_list
        assert calls[0].kwargs["device_id"] == 4
        assert calls[1].kwargs["device_id"] == 3

    async def test_read_not_connected_raises(self) -> None:
        machine = _make_machine()
        driver = ModbusDriver(machine)

        with pytest.raises(ConnectionError, match="Not connected"):
            await driver.read_temperatures()


# ── read_extra_channels tests ─────────────────────────────────────────


class TestReadExtraChannels:
    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_reads_all_extra_channels(self, mock_cls: MagicMock) -> None:
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_client.read_holding_registers = AsyncMock(
            side_effect=[_mock_response([750]), _mock_response([480]), _mock_response([60])]
        )
        mock_cls.return_value = mock_client

        machine = _make_machine(
            extra_channels=[
                ChannelConfig(
                    name="Burner",
                    modbus=ModbusRegisterConfig(address=45, divisor=1, mode=""),
                ),
                ChannelConfig(
                    name="Drum",
                    modbus=ModbusRegisterConfig(address=46, divisor=1, mode=""),
                ),
                ChannelConfig(
                    name="Air",
                    modbus=ModbusRegisterConfig(address=47, divisor=0, mode=""),
                ),
            ],
        )
        driver = ModbusDriver(machine)
        await driver.connect()

        result = await driver.read_extra_channels()
        assert result == {
            "Burner": pytest.approx(75.0),
            "Drum": pytest.approx(48.0),
            "Air": pytest.approx(60.0),
        }

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_channel_read_failure_returns_zero(self, mock_cls: MagicMock) -> None:
        """Individual channel failure doesn't prevent reading others."""
        from pymodbus.exceptions import ModbusIOException

        mock_client = AsyncMock()
        mock_client.connected = True
        mock_client.read_holding_registers = AsyncMock(
            side_effect=[ModbusIOException("fail"), _mock_response([500])]
        )
        mock_cls.return_value = mock_client

        machine = _make_machine(
            extra_channels=[
                ChannelConfig(
                    name="Bad",
                    modbus=ModbusRegisterConfig(address=100, divisor=0, mode=""),
                ),
                ChannelConfig(
                    name="Good",
                    modbus=ModbusRegisterConfig(address=101, divisor=0, mode=""),
                ),
            ],
        )
        driver = ModbusDriver(machine)
        await driver.connect()

        result = await driver.read_extra_channels()
        assert result["Bad"] == 0.0
        assert result["Good"] == pytest.approx(500.0)

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_no_extra_channels(self, mock_cls: MagicMock) -> None:
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_cls.return_value = mock_client

        machine = _make_machine(extra_channels=[])
        driver = ModbusDriver(machine)
        await driver.connect()

        result = await driver.read_extra_channels()
        assert result == {}


# ── Command parsing and execution tests ───────────────────────────────


class TestCommandExecution:
    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_write_single_standard(self, mock_cls: MagicMock) -> None:
        """writeSingle(unit_id, address, value) format."""
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_cls.return_value = mock_client

        machine = _make_machine(controls=[
            ControlConfig(
                name="Air", channel="air", command="writeSingle(1,47,{})",
                min=0, max=120,
            ),
        ])
        driver = ModbusDriver(machine)
        await driver.connect()

        await driver.write_control("air", 60.0)

        mock_client.write_register.assert_awaited_once_with(47, 60, device_id=1)

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_write_single_bracket_syntax(self, mock_cls: MagicMock) -> None:
        """writeSingle([unit_id, address, value]) format (Coffed)."""
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_cls.return_value = mock_client

        machine = _make_machine(controls=[
            ControlConfig(
                name="Slider 1",
                channel="slider1",
                command="writeSingle([1,1,{}])",
                min=0,
                max=100,
            ),
        ])
        driver = ModbusDriver(machine)
        await driver.connect()

        await driver.write_control("slider1", 75.0)

        mock_client.write_register.assert_awaited_once_with(1, 75, device_id=1)

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_compound_command(self, mock_cls: MagicMock) -> None:
        """Compound command with writeSingle + mwrite (Probat)."""
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_cls.return_value = mock_client

        machine = _make_machine(controls=[
            ControlConfig(
                name="Burner",
                channel="burner",
                command="writeSingle(1,12290,{});mwrite(1,12318,65531,4)",
                min=0,
                max=100,
            ),
        ])
        driver = ModbusDriver(machine)
        await driver.connect()

        await driver.write_control("burner", 50.0)

        mock_client.write_register.assert_awaited_once_with(12290, 50, device_id=1)
        mock_client.mask_write_register.assert_awaited_once_with(
            address=12318, and_mask=4, or_mask=65531, device_id=1
        )

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_write_unknown_channel_raises(self, mock_cls: MagicMock) -> None:
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_cls.return_value = mock_client

        machine = _make_machine(controls=[])
        driver = ModbusDriver(machine)
        await driver.connect()

        with pytest.raises(NotImplementedError, match="not configured"):
            await driver.write_control("nonexistent", 50.0)

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_write_empty_command_raises(self, mock_cls: MagicMock) -> None:
        mock_client = AsyncMock()
        mock_client.connected = True
        mock_cls.return_value = mock_client

        machine = _make_machine(controls=[
            ControlConfig(name="No Cmd", channel="nocmd", command="", min=0, max=100),
        ])
        driver = ModbusDriver(machine)
        await driver.connect()

        with pytest.raises(NotImplementedError, match="no command template"):
            await driver.write_control("nocmd", 50.0)

    @patch("openroast.drivers.modbus.AsyncModbusTcpClient")
    async def test_write_connection_failure(self, mock_cls: MagicMock) -> None:
        """Write failure sets error state."""
        from pymodbus.exceptions import ConnectionException

        mock_client = AsyncMock()
        mock_client.connected = True
        mock_client.write_register = AsyncMock(side_effect=ConnectionException("timeout"))
        mock_cls.return_value = mock_client

        machine = _make_machine(controls=[
            ControlConfig(
                name="Air", channel="air", command="writeSingle(1,47,{})",
                min=0, max=100,
            ),
        ])
        driver = ModbusDriver(machine)
        await driver.connect()

        with pytest.raises(ConnectionError, match="Modbus write failed"):
            await driver.write_control("air", 50.0)

        assert driver.state == ConnectionState.ERROR

    async def test_write_not_connected_raises(self) -> None:
        machine = _make_machine(controls=[
            ControlConfig(
                name="Air", channel="air", command="writeSingle(1,47,{})",
                min=0, max=100,
            ),
        ])
        driver = ModbusDriver(machine)

        with pytest.raises(ConnectionError, match="Not connected"):
            await driver.write_control("air", 50.0)


# ── Float decode tests ────────────────────────────────────────────────


class TestDecodeFloat:
    def test_little_endian_word_order(self) -> None:
        import struct

        packed = struct.pack(">f", 123.456)
        high, low = struct.unpack(">HH", packed)
        # Little endian: [low, high]
        result = ModbusDriver._decode_float([low, high], word_order_little=True)
        assert result == pytest.approx(123.456, rel=1e-4)

    def test_big_endian_word_order(self) -> None:
        import struct

        packed = struct.pack(">f", 789.012)
        high, low = struct.unpack(">HH", packed)
        # Big endian: [high, low]
        result = ModbusDriver._decode_float([high, low], word_order_little=False)
        assert result == pytest.approx(789.012, rel=1e-4)

    def test_zero(self) -> None:
        result = ModbusDriver._decode_float([0, 0], word_order_little=True)
        assert result == pytest.approx(0.0)
