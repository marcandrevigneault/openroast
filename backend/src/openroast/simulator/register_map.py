"""Build a pymodbus server context from a catalog machine definition.

Converts ``CatalogModel`` channel and control configs into a
``ModbusServerContext`` whose registers mirror the machine's real
register layout. Encoding helpers ensure values are stored in the
same format the driver expects (signed int16, BCD, IEEE 754 float).
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pymodbus.datastore import (
    ModbusDeviceContext,
    ModbusServerContext,
    ModbusSparseDataBlock,
)

if TYPE_CHECKING:
    from openroast.models.catalog import CatalogModel, ControlConfig, ModbusRegisterConfig

# Divisor multiplier lookup (inverse of driver's divide)
_DIVISOR_MULT = {0: 1, 1: 10, 2: 100, 3: 1000}

# pymodbus ModbusDeviceContext applies a +1 offset when translating
# protocol addresses to datablock indices.  When building the initial
# ModbusSparseDataBlock we must therefore store values at (address + 1).
_ADDR_OFFSET = 1


def _celsius_to_fahrenheit(c: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return c * 9.0 / 5.0 + 32.0


def _int_to_bcd(value: int) -> int:
    """Encode an integer as BCD in a 16-bit register.

    Args:
        value: Non-negative integer (e.g. 215 → 0x0215).

    Returns:
        BCD-encoded 16-bit value.
    """
    if value < 0:
        value = 0
    result = 0
    shift = 0
    while value > 0:
        digit = value % 10
        result |= digit << shift
        shift += 4
        value //= 10
    return result


def encode_value(
    value: float,
    config: ModbusRegisterConfig,
    word_order_little: bool = True,
) -> list[int]:
    """Encode a float into register value(s) matching the driver's decode.

    The driver reads registers and decodes them; this function does the
    reverse — it takes a real value and encodes it so the driver will
    read back the original.

    Args:
        value: Value in natural units (Celsius for temps, raw for others).
        config: Register configuration describing the encoding.
        word_order_little: Float word order (matches connection config).

    Returns:
        List of 16-bit register values (1 for int16/BCD, 2 for float32).
    """
    # Temperature mode: convert C → F if the register stores Fahrenheit
    if config.mode == "F":
        value = _celsius_to_fahrenheit(value)

    # Apply divisor (multiply, inverse of driver's divide)
    multiplier = _DIVISOR_MULT.get(config.divisor, 1)
    if multiplier > 1:
        value *= multiplier

    if config.is_float:
        # IEEE 754 float32 → two 16-bit registers
        packed = struct.pack(">f", value)
        high, low = struct.unpack(">HH", packed)
        if word_order_little:
            return [low, high]
        return [high, low]

    if config.is_bcd:
        return [_int_to_bcd(round(value))]

    # Signed 16-bit integer
    raw = round(value)
    raw = max(-32768, min(32767, raw))
    if raw < 0:
        raw += 0x10000
    return [raw]


@dataclass
class _DeviceRegisters:
    """Registers grouped by function code for one device_id."""

    # Keys are block indices (protocol address + _ADDR_OFFSET)
    holding: dict[int, int] = field(default_factory=dict)  # FC3
    input_: dict[int, int] = field(default_factory=dict)  # FC4


def _collect_channel_registers(
    config: ModbusRegisterConfig,
    initial_value: float,
    word_order_little: bool,
    devices: dict[int, _DeviceRegisters],
) -> None:
    """Add a channel's registers to the device map."""
    dev = devices.setdefault(config.device_id, _DeviceRegisters())
    encoded = encode_value(initial_value, config, word_order_little)

    target = dev.holding if config.code == 3 else dev.input_
    for i, val in enumerate(encoded):
        target[config.address + _ADDR_OFFSET + i] = val


def _parse_control_address(control: ControlConfig) -> tuple[int, int] | None:
    """Extract (device_id, address) from a writeSingle command template.

    Returns:
        Tuple of (device_id, address) or None if unparseable.
    """
    cmd = control.command
    if not cmd:
        return None

    # Handle first command in compound commands
    first_cmd = cmd.split(";")[0].strip()
    match = re.match(r"writeSingle\(\[?\s*(\d+)\s*,\s*(\d+)\s*,", first_cmd)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def build_server_context(
    model: CatalogModel,
    initial_bt: float = 25.0,
    initial_et: float = 25.0,
) -> ModbusServerContext:
    """Build a pymodbus server context from a catalog model.

    Creates register blocks for all channels (BT, ET, extra) and
    control addresses, grouped by device_id and function code.

    Args:
        model: Catalog machine definition.
        initial_bt: Initial bean temperature in Celsius.
        initial_et: Initial environment temperature in Celsius.

    Returns:
        ModbusServerContext ready for use with ModbusTcpServer.
    """
    from openroast.models.catalog import ModbusConnectionConfig

    conn = model.connection
    word_order_little = True
    if isinstance(conn, ModbusConnectionConfig):
        word_order_little = conn.word_order_little

    devices: dict[int, _DeviceRegisters] = {}

    # BT channel
    if model.bt and model.bt.modbus:
        _collect_channel_registers(
            model.bt.modbus, initial_bt, word_order_little, devices,
        )

    # ET channel
    if model.et and model.et.modbus:
        _collect_channel_registers(
            model.et.modbus, initial_et, word_order_little, devices,
        )

    # Extra channels (initialize to 0)
    for ch in model.extra_channels:
        if ch.modbus:
            _collect_channel_registers(
                ch.modbus, 0.0, word_order_little, devices,
            )

    # Control addresses (writable holding registers, init to 0)
    for ctrl in model.controls:
        parsed = _parse_control_address(ctrl)
        if parsed:
            device_id, address = parsed
            dev = devices.setdefault(device_id, _DeviceRegisters())
            dev.holding.setdefault(address + _ADDR_OFFSET, 0)

    # Build pymodbus context
    device_contexts: dict[int, ModbusDeviceContext] = {}
    for device_id, regs in devices.items():
        hr = ModbusSparseDataBlock(regs.holding) if regs.holding else None
        ir = ModbusSparseDataBlock(regs.input_) if regs.input_ else None
        device_contexts[device_id] = ModbusDeviceContext(hr=hr, ir=ir)

    return ModbusServerContext(devices=device_contexts, single=False)


def write_channel(
    context: ModbusServerContext,
    config: ModbusRegisterConfig,
    value: float,
    word_order_little: bool = True,
) -> None:
    """Write an encoded value to the server context for a channel.

    Uses ``ModbusDeviceContext.setValues`` which handles the internal
    address offset automatically.

    Args:
        context: The server context to update.
        config: Register configuration for the channel.
        value: Value in natural units (Celsius for temps).
        word_order_little: Float word order.
    """
    encoded = encode_value(value, config, word_order_little)
    device_ctx = context[config.device_id]
    device_ctx.setValues(config.code, config.address, encoded)


def read_register_raw(
    context: ModbusServerContext,
    device_id: int,
    address: int,
    code: int = 3,
) -> int:
    """Read a single raw 16-bit register value from the server context.

    Uses ``ModbusDeviceContext.getValues`` which handles the internal
    address offset automatically.

    Args:
        context: The server context.
        device_id: Modbus device/slave ID.
        address: Register address.
        code: Function code (3=holding, 4=input).

    Returns:
        Raw 16-bit register value.
    """
    device_ctx = context[device_id]
    values = device_ctx.getValues(code, address, 1)
    return values[0]
