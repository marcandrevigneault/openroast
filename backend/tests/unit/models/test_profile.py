"""Unit tests for Pydantic data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from openroast.models.profile import (
    MachineConfig,
    RoastEvent,
    RoastProfile,
    TemperaturePoint,
)


class TestTemperaturePoint:
    def test_valid_point(self) -> None:
        p = TemperaturePoint(timestamp_ms=3000, et=210.5, bt=155.2)
        assert p.timestamp_ms == 3000
        assert p.et == 210.5

    def test_negative_timestamp_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TemperaturePoint(timestamp_ms=-1, et=200.0, bt=150.0)


class TestRoastEvent:
    def test_defaults(self) -> None:
        e = RoastEvent(event_type="CHARGE", timestamp_ms=5000)
        assert e.auto_detected is False

    def test_auto_detected(self) -> None:
        e = RoastEvent(event_type="DROP", timestamp_ms=600000, auto_detected=True)
        assert e.auto_detected is True


class TestRoastProfile:
    def test_minimal_profile(self) -> None:
        p = RoastProfile(name="Test Roast")
        assert p.name == "Test Roast"
        assert p.temperatures == []
        assert p.events == []

    def test_full_profile(self) -> None:
        p = RoastProfile(
            name="Ethiopian Natural",
            machine="Stratto 2.0",
            bean_name="Yirgacheffe",
            bean_weight_g=500,
            bean_moisture_pct=10.5,
            temperatures=[
                TemperaturePoint(timestamp_ms=0, et=210, bt=155),
                TemperaturePoint(timestamp_ms=3000, et=212, bt=160),
            ],
            events=[
                RoastEvent(event_type="CHARGE", timestamp_ms=0),
            ],
        )
        assert len(p.temperatures) == 2
        assert len(p.events) == 1
        assert p.bean_weight_g == 500

    def test_serialization_roundtrip(self) -> None:
        p = RoastProfile(
            name="Test",
            temperatures=[TemperaturePoint(timestamp_ms=0, et=200, bt=150)],
        )
        data = p.model_dump()
        p2 = RoastProfile.model_validate(data)
        assert p2.name == p.name
        assert len(p2.temperatures) == 1


class TestMachineConfig:
    def test_defaults(self) -> None:
        c = MachineConfig(name="Stratto", driver="modbus_rtu")
        assert c.host == "localhost"
        assert c.port == 502
        assert c.sampling_interval_ms == 3000

    def test_custom_values(self) -> None:
        c = MachineConfig(
            name="Remote Roaster",
            driver="tcp",
            host="192.168.1.100",
            port=5020,
            sampling_interval_ms=1000,
        )
        assert c.host == "192.168.1.100"
        assert c.sampling_interval_ms == 1000

    def test_sampling_interval_bounds(self) -> None:
        with pytest.raises(ValidationError):
            MachineConfig(name="x", driver="x", sampling_interval_ms=100)
        with pytest.raises(ValidationError):
            MachineConfig(name="x", driver="x", sampling_interval_ms=20000)
