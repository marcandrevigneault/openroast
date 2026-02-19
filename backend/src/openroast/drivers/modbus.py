"""Modbus RTU and TCP driver for roaster communication.

Supports all machines using MODBUS protocol in the catalog (Carmomaq,
Loring, Coffed, Diedrich, Besca, Probat, Toper, US Roaster Corp, Mill City).
Uses pymodbus async client for non-blocking communication.
"""

from __future__ import annotations

import logging
import re
import struct
from typing import TYPE_CHECKING

from pymodbus.client import AsyncModbusSerialClient, AsyncModbusTcpClient
from pymodbus.exceptions import ConnectionException, ModbusIOException

from openroast.drivers.base import BaseDriver, ConnectionState, DriverInfo, TemperatureReading
from openroast.models.catalog import ModbusRegisterConfig, ProtocolType

if TYPE_CHECKING:
    from pymodbus.client import AsyncModbusSerialClient as SerialClient
    from pymodbus.client import AsyncModbusTcpClient as TcpClient

    from openroast.models.catalog import ControlConfig, ModbusConnectionConfig
    from openroast.models.machine import SavedMachine

logger = logging.getLogger(__name__)

# Divisor lookup: index → divide-by value
_DIVISORS = {0: 1, 1: 10, 2: 100, 3: 1000}


def _bcd_to_int(value: int) -> int:
    """Decode a BCD-encoded 16-bit register value to an integer.

    Args:
        value: Raw 16-bit BCD value (e.g. 0x0215 → 215).

    Returns:
        Decoded integer.
    """
    result = 0
    multiplier = 1
    while value > 0:
        digit = value & 0x0F
        result += digit * multiplier
        multiplier *= 10
        value >>= 4
    return result


def _fahrenheit_to_celsius(f: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return (f - 32.0) * 5.0 / 9.0


class ModbusDriver(BaseDriver):
    """Driver for Modbus RTU and TCP roasting machines.

    Args:
        machine: Saved machine configuration with Modbus connection details.
    """

    def __init__(self, machine: SavedMachine) -> None:
        if machine.protocol not in (ProtocolType.MODBUS_RTU, ProtocolType.MODBUS_TCP):
            msg = f"ModbusDriver requires modbus_rtu or modbus_tcp, got {machine.protocol}"
            raise ValueError(msg)

        self._machine = machine
        self._conn: ModbusConnectionConfig = machine.connection  # type: ignore[assignment]
        self._client: TcpClient | SerialClient | None = None
        self._state = ConnectionState.DISCONNECTED

        # Build control lookup: channel name → ControlConfig
        self._controls: dict[str, ControlConfig] = {c.channel: c for c in machine.controls}

    async def connect(self) -> None:
        """Establish connection to the Modbus device."""
        if self._state == ConnectionState.CONNECTED:
            return

        self._state = ConnectionState.CONNECTING
        try:
            if self._machine.protocol == ProtocolType.MODBUS_TCP:
                self._client = AsyncModbusTcpClient(
                    self._conn.host,
                    port=self._conn.port,
                    timeout=self._conn.timeout,
                )
            else:
                self._client = AsyncModbusSerialClient(
                    self._conn.host,
                    baudrate=self._conn.baudrate,
                    bytesize=self._conn.bytesize,
                    parity=self._conn.parity,
                    stopbits=self._conn.stopbits,
                    timeout=self._conn.timeout,
                )
            await self._client.connect()
            if not self._client.connected:
                raise ConnectionError("Failed to establish Modbus connection")
            self._state = ConnectionState.CONNECTED
            logger.info("Connected to %s at %s", self._machine.name, self._conn.host)
        except Exception:
            self._state = ConnectionState.ERROR
            self._client = None
            raise

    async def disconnect(self) -> None:
        """Close the Modbus connection."""
        if self._client is not None:
            self._client.close()
            self._client = None
        self._state = ConnectionState.DISCONNECTED
        logger.info("Disconnected from %s", self._machine.name)

    async def read_temperatures(self) -> TemperatureReading:
        """Read ET and BT from Modbus registers.

        Returns:
            TemperatureReading with ET/BT in Celsius.

        Raises:
            ConnectionError: If not connected or communication fails.
        """
        self._ensure_connected()

        et = 0.0
        bt = 0.0

        if self._machine.et and self._machine.et.modbus:
            et = await self._read_register(self._machine.et.modbus)
        if self._machine.bt and self._machine.bt.modbus:
            bt = await self._read_register(self._machine.bt.modbus)

        return TemperatureReading(et=et, bt=bt, timestamp_ms=0.0)

    async def read_extra_channels(self) -> dict[str, float]:
        """Read all extra channels from Modbus registers.

        Returns:
            Dict mapping channel name to value.
        """
        self._ensure_connected()

        result: dict[str, float] = {}
        for ch in self._machine.extra_channels:
            if ch.modbus:
                try:
                    result[ch.name] = await self._read_register(ch.modbus)
                except (ConnectionError, ModbusIOException) as e:
                    logger.warning("Failed to read channel %s: %s", ch.name, e)
                    result[ch.name] = 0.0
        return result

    async def write_control(self, channel: str, value: float) -> None:
        """Write a control value to the roaster.

        Args:
            channel: Control channel name (must match a ControlConfig.channel).
            value: Value in native units (e.g. 0-100 for percentage).

        Raises:
            NotImplementedError: If channel is not in machine controls.
            ConnectionError: If not connected.
        """
        self._ensure_connected()

        control = self._controls.get(channel)
        if control is None:
            raise NotImplementedError(
                f"Control channel '{channel}' not configured for {self._machine.name}"
            )

        if not control.command:
            raise NotImplementedError(
                f"Control '{channel}' has no command template"
            )

        await self._execute_command(control.command, int(value))

    def info(self) -> DriverInfo:
        """Return driver metadata."""
        return DriverInfo(
            name=f"Modbus {'RTU' if self._machine.protocol == ProtocolType.MODBUS_RTU else 'TCP'}",
            manufacturer=self._machine.catalog_manufacturer_id or "Custom",
            model=self._machine.name,
            protocol=self._machine.protocol.value,
        )

    @property
    def state(self) -> ConnectionState:
        """Current connection state."""
        return self._state

    # ── Internal helpers ──────────────────────────────────────────────

    def _ensure_connected(self) -> None:
        """Raise ConnectionError if not connected."""
        if self._state != ConnectionState.CONNECTED or self._client is None:
            raise ConnectionError("Not connected to Modbus device")

    async def _read_register(self, config: ModbusRegisterConfig) -> float:
        """Read a single value from a Modbus register.

        Handles function codes, divisors, float decoding, BCD decoding,
        and Fahrenheit conversion.

        Args:
            config: Register configuration from the catalog.

        Returns:
            Decoded value (in Celsius if mode is "F" or "C").

        Raises:
            ConnectionError: On communication failure.
        """
        assert self._client is not None

        count = 2 if config.is_float else 1

        try:
            if config.code == 3:
                resp = await self._client.read_holding_registers(
                    config.address, count=count, device_id=config.device_id
                )
            elif config.code == 4:
                resp = await self._client.read_input_registers(
                    config.address, count=count, device_id=config.device_id
                )
            else:
                msg = f"Unsupported function code: {config.code}"
                raise ValueError(msg)
        except (ConnectionException, ModbusIOException) as e:
            self._state = ConnectionState.ERROR
            raise ConnectionError(f"Modbus read failed: {e}") from e

        if resp.isError():
            raise ConnectionError(f"Modbus error response: {resp}")

        registers: list[int] = resp.registers

        # Decode the raw register(s) to a float
        if config.is_float:
            value = self._decode_float(registers, self._conn.word_order_little)
        elif config.is_bcd:
            value = float(_bcd_to_int(registers[0]))
        else:
            # Treat as signed 16-bit integer
            raw = registers[0]
            if raw >= 0x8000:
                raw -= 0x10000
            value = float(raw)

        # Apply divisor
        divisor = _DIVISORS.get(config.divisor, 1)
        if divisor > 1:
            value /= divisor

        # Temperature mode conversion
        if config.mode == "F":
            value = _fahrenheit_to_celsius(value)

        return value

    @staticmethod
    def _decode_float(registers: list[int], word_order_little: bool) -> float:
        """Decode two 16-bit registers into a 32-bit IEEE 754 float.

        Args:
            registers: Two register values [high_word, low_word] or [low_word, high_word].
            word_order_little: If True, first register is the low word.

        Returns:
            Decoded float value.
        """
        if word_order_little:
            low, high = registers[0], registers[1]
        else:
            high, low = registers[0], registers[1]

        packed = struct.pack(">HH", high, low)
        return struct.unpack(">f", packed)[0]

    async def _execute_command(self, command_template: str, value: int) -> None:
        """Parse and execute a control command template.

        Supports compound commands separated by ';', e.g.:
            "writeSingle(1,12290,{});mwrite(1,12318,65531,4)"

        Args:
            command_template: Command string with {} placeholder for value.
            value: Integer value to insert.

        Raises:
            ConnectionError: On communication failure.
            ValueError: On unparseable command.
        """
        # Replace {} with the actual value
        command_str = command_template.replace("{}", str(value))

        # Split compound commands on ';'
        for cmd in command_str.split(";"):
            cmd = cmd.strip()
            if not cmd:
                continue
            await self._execute_single_command(cmd)

    async def _execute_single_command(self, cmd: str) -> None:
        """Execute a single parsed command string.

        Supported formats:
            writeSingle(device_id, address, value)
            writeSingle([device_id, address, value])
            mwrite(device_id, address, value, mask)

        Args:
            cmd: Fully resolved command string (no {} placeholders).
        """
        assert self._client is not None

        # Parse the command: function_name(args...)
        match = re.match(r"(\w+)\((.+)\)", cmd)
        if not match:
            msg = f"Cannot parse command: {cmd}"
            raise ValueError(msg)

        func_name = match.group(1)
        args_str = match.group(2).strip()

        # Handle bracket syntax: writeSingle([1, 2, 3])
        if args_str.startswith("[") and args_str.endswith("]"):
            args_str = args_str[1:-1]

        args = [int(a.strip()) for a in args_str.split(",")]

        try:
            if func_name == "writeSingle":
                if len(args) != 3:
                    msg = f"writeSingle expects 3 args, got {len(args)}: {cmd}"
                    raise ValueError(msg)
                device_id, address, val = args
                await self._client.write_register(address, val, device_id=device_id)

            elif func_name == "mwrite":
                if len(args) != 4:
                    msg = f"mwrite expects 4 args, got {len(args)}: {cmd}"
                    raise ValueError(msg)
                device_id, address, or_mask, and_mask = args
                await self._client.mask_write_register(
                    address=address,
                    and_mask=and_mask,
                    or_mask=or_mask,
                    device_id=device_id,
                )

            else:
                msg = f"Unknown command function: {func_name}"
                raise ValueError(msg)

        except (ConnectionException, ModbusIOException) as e:
            self._state = ConnectionState.ERROR
            raise ConnectionError(f"Modbus write failed: {e}") from e
