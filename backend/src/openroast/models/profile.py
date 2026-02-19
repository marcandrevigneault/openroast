"""Pydantic models for roast profiles and session data."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TemperaturePoint(BaseModel):
    """A single data point in a roast profile."""

    timestamp_ms: float = Field(ge=0, description="Milliseconds since roast start")
    et: float = Field(description="Environment temperature (Celsius)")
    bt: float = Field(description="Bean temperature (Celsius)")


class RoastEvent(BaseModel):
    """A roast event (CHARGE, DRY, FCs, FCe, SCs, DROP, COOL)."""

    event_type: str = Field(description="Event identifier")
    timestamp_ms: float = Field(ge=0, description="When the event occurred")
    auto_detected: bool = Field(default=False, description="Was this auto-detected?")


class RoastProfile(BaseModel):
    """A complete roast profile — recorded or loaded for replay."""

    id: str | None = Field(default=None, description="Unique profile ID")
    name: str = Field(description="Profile display name")
    machine: str = Field(default="", description="Machine name")
    created_at: datetime = Field(default_factory=datetime.now)
    bean_name: str = Field(default="")
    bean_weight_g: float = Field(default=0, ge=0)
    bean_moisture_pct: float = Field(default=0, ge=0, le=100)

    # Time series data
    temperatures: list[TemperaturePoint] = Field(default_factory=list)
    extra_channels: dict[str, list[float]] = Field(default_factory=dict)

    # Events
    events: list[RoastEvent] = Field(default_factory=list)

    # Control curves (slider values over time for replay)
    controls: dict[str, list[tuple[float, float]]] = Field(default_factory=dict)


class MachineConfig(BaseModel):
    """Configuration for a roasting machine connection."""

    name: str = Field(description="Display name for this machine")
    driver: str = Field(description="Driver identifier (e.g., 'modbus_rtu')")
    host: str = Field(default="localhost")
    port: int = Field(default=502)
    sampling_interval_ms: int = Field(default=3000, ge=500, le=10000)
    extra_params: dict[str, str] = Field(default_factory=dict)
