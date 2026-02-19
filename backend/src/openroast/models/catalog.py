"""Pydantic models for the machine catalog and protocol configurations.

The catalog is a static list of known roasting machines with their default
connection parameters. Protocol config schemas use discriminated unions
to handle different communication protocols (MODBUS, Serial, S7).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

# ── Protocol enums ──────────────────────────────────────────────────


class ProtocolType(StrEnum):
    """Supported communication protocols."""

    MODBUS_RTU = "modbus_rtu"
    MODBUS_TCP = "modbus_tcp"
    SERIAL = "serial"
    S7 = "s7"


# ── Register / channel configs ──────────────────────────────────────


class ModbusRegisterConfig(BaseModel):
    """Configuration for reading a single MODBUS register."""

    address: int = Field(ge=0, description="Register address")
    code: int = Field(default=3, ge=1, le=4, description="Function code (3=holding, 4=input)")
    device_id: int = Field(default=1, ge=0, le=247, description="Slave/unit ID")
    divisor: int = Field(default=0, ge=0, le=3, description="0=none, 1=/10, 2=/100, 3=/1000")
    mode: str = Field(default="C", description="C=Celsius, F=Fahrenheit, empty=raw")
    is_float: bool = Field(default=False, description="Read as 32-bit IEEE float")
    is_bcd: bool = Field(default=False, description="BCD-encoded value")


class S7RegisterConfig(BaseModel):
    """Configuration for reading a single S7 PLC data point."""

    area: int = Field(default=6, ge=0, description="S7 area (6=DB, 0=PE, 1=PA, 2=MK)")
    db_nr: int = Field(default=2, ge=0, description="Data block number")
    start: int = Field(ge=0, description="Byte offset in the block")
    type: int = Field(default=0, ge=0, le=2, description="0=int16, 1=float32, 2=intFloat")
    mode: int = Field(default=1, ge=0, le=2, description="0=raw, 1=Celsius, 2=Fahrenheit")
    div: int = Field(default=0, ge=0, le=2, description="0=none, 1=/10, 2=/100")


class ChannelConfig(BaseModel):
    """A temperature or data channel configuration."""

    name: str = Field(description="Channel display name")
    modbus: ModbusRegisterConfig | None = Field(default=None)
    s7: S7RegisterConfig | None = Field(default=None)


class ControlConfig(BaseModel):
    """Configuration for a control slider (burner, airflow, etc.)."""

    name: str = Field(description="Display name")
    channel: str = Field(description="Control channel ID (e.g. 'burner')")
    command: str = Field(default="", description="Command template with {} placeholder")
    min: float = Field(default=0)
    max: float = Field(default=100)
    step: float = Field(default=1)
    unit: str = Field(default="")


# ── Protocol-specific connection configs ─────────────────────────────


class ModbusConnectionConfig(BaseModel):
    """MODBUS RTU or TCP connection parameters."""

    type: Literal["modbus_rtu", "modbus_tcp"] = "modbus_tcp"
    host: str = Field(default="192.168.1.1", description="TCP host or serial port path")
    port: int = Field(default=502, ge=1, le=65535)
    baudrate: int = Field(default=19200, description="Serial baudrate (RTU only)")
    bytesize: int = Field(default=8, ge=5, le=8)
    parity: str = Field(default="N", description="N=None, E=Even, O=Odd")
    stopbits: int = Field(default=1, ge=1, le=2)
    timeout: float = Field(default=1.0, gt=0, le=30)
    word_order_little: bool = Field(default=True, description="Little-endian word order for floats")


class SerialConnectionConfig(BaseModel):
    """Serial port connection parameters."""

    type: Literal["serial"] = "serial"
    comport: str = Field(default="/dev/ttyUSB0", description="Serial port path")
    baudrate: int = Field(default=115200)
    bytesize: int = Field(default=8, ge=5, le=8)
    parity: str = Field(default="N", description="N=None, E=Even, O=Odd")
    stopbits: int = Field(default=1, ge=1, le=2)
    timeout: float = Field(default=1.0, gt=0, le=30)


class S7ConnectionConfig(BaseModel):
    """Siemens S7 PLC connection parameters."""

    type: Literal["s7"] = "s7"
    host: str = Field(default="192.168.1.1")
    port: int = Field(default=102, ge=1, le=65535)
    rack: int = Field(default=0, ge=0)
    slot: int = Field(default=0, ge=0)


ConnectionConfig = Annotated[
    ModbusConnectionConfig | SerialConnectionConfig | S7ConnectionConfig,
    Field(discriminator="type"),
]


# ── Catalog models ───────────────────────────────────────────────────


class CatalogModel(BaseModel):
    """A single roasting machine model in the catalog."""

    id: str = Field(description="Unique model identifier")
    name: str = Field(description="Display name")
    protocol: ProtocolType
    sampling_interval_ms: int = Field(default=3000, ge=500, le=10000)
    connection: ConnectionConfig
    et: ChannelConfig | None = Field(default=None, description="ET channel config")
    bt: ChannelConfig | None = Field(default=None, description="BT channel config")
    extra_channels: list[ChannelConfig] = Field(default_factory=list)
    controls: list[ControlConfig] = Field(default_factory=list)


class CatalogManufacturer(BaseModel):
    """A roaster manufacturer with its available models."""

    id: str = Field(description="URL-safe manufacturer ID")
    name: str = Field(description="Display name")
    country: str = Field(default="", description="ISO country code")
    models: list[CatalogModel] = Field(default_factory=list)


class MachineCatalog(BaseModel):
    """The complete machine catalog."""

    version: int = Field(default=1)
    manufacturers: list[CatalogManufacturer] = Field(default_factory=list)
