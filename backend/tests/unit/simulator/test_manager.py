"""Tests for the simulator manager."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from openroast.catalog.loader import get_model
from openroast.core.machine_storage import MachineStorage
from openroast.models.catalog import (
    CatalogModel,
    ChannelConfig,
    ModbusConnectionConfig,
    ModbusRegisterConfig,
    ProtocolType,
)
from openroast.simulator.manager import SimulatorManager, _find_free_port


def _make_model() -> CatalogModel:
    return CatalogModel(
        id="test-sim",
        name="Test Simulator",
        protocol=ProtocolType.MODBUS_TCP,
        sampling_interval_ms=1000,
        connection=ModbusConnectionConfig(type="modbus_tcp"),
        bt=ChannelConfig(
            name="BT",
            modbus=ModbusRegisterConfig(address=43, code=3, device_id=1),
        ),
        et=ChannelConfig(
            name="ET",
            modbus=ModbusRegisterConfig(address=44, code=3, device_id=1),
        ),
    )


class TestFindFreePort:
    def test_returns_positive_int(self) -> None:
        port = _find_free_port()
        assert isinstance(port, int)
        assert port > 0


class TestSimulatorManager:
    @pytest.mark.asyncio
    async def test_start_and_list(self) -> None:
        manager = SimulatorManager()
        model = _make_model()
        port = _find_free_port()

        info = await manager.start(model, "test-mfr", port=port)
        try:
            assert info.catalog_id == "test-sim"
            assert info.port == port
            assert info.name == "Test Simulator"

            running = manager.list_running()
            assert len(running) == 1
            assert running[0].machine_id == info.machine_id
        finally:
            await manager.stop_all()

    @pytest.mark.asyncio
    async def test_stop_removes_instance(self) -> None:
        manager = SimulatorManager()
        model = _make_model()
        port = _find_free_port()

        info = await manager.start(model, "test-mfr", port=port)
        await manager.stop(info.machine_id)

        assert manager.list_running() == []
        assert manager.get(info.machine_id) is None

    @pytest.mark.asyncio
    async def test_stop_nonexistent_raises(self) -> None:
        manager = SimulatorManager()
        with pytest.raises(KeyError):
            await manager.stop("nonexistent")

    @pytest.mark.asyncio
    async def test_multiple_same_model_allowed(self) -> None:
        manager = SimulatorManager()
        model = _make_model()

        info1 = await manager.start(model, "test-mfr", port=_find_free_port())
        try:
            info2 = await manager.start(model, "test-mfr", port=_find_free_port())
            assert info1.machine_id != info2.machine_id
            assert info1.port != info2.port
            assert len(manager.list_running()) == 2
        finally:
            await manager.stop_all()

    @pytest.mark.asyncio
    async def test_custom_name(self) -> None:
        manager = SimulatorManager()
        model = _make_model()

        info = await manager.start(
            model, "test-mfr", port=_find_free_port(), name="My Custom Sim",
        )
        try:
            assert info.name == "My Custom Sim"
        finally:
            await manager.stop_all()

    @pytest.mark.asyncio
    async def test_default_name_from_model(self) -> None:
        manager = SimulatorManager()
        model = _make_model()

        info = await manager.start(model, "test-mfr", port=_find_free_port())
        try:
            assert info.name == "Test Simulator"
        finally:
            await manager.stop_all()

    @pytest.mark.asyncio
    async def test_custom_name_saved_machine(self, tmp_path: Path) -> None:
        storage = MachineStorage(tmp_path / "machines")
        manager = SimulatorManager(machine_storage=storage)
        model = _make_model()

        info = await manager.start(
            model, "test-mfr", port=_find_free_port(), name="Renamed Sim",
        )
        try:
            saved = storage.get(info.machine_id)
            assert saved is not None
            assert saved.name == "Renamed Sim"
        finally:
            await manager.stop_all()

    @pytest.mark.asyncio
    async def test_creates_saved_machine(self, tmp_path: Path) -> None:
        storage = MachineStorage(tmp_path / "machines")
        manager = SimulatorManager(machine_storage=storage)
        model = _make_model()
        port = _find_free_port()

        info = await manager.start(model, "test-mfr", port=port)
        try:
            # Check that a SavedMachine was created in storage
            saved = storage.get(info.machine_id)
            assert saved is not None
            assert saved.name == "Test Simulator"
            assert saved.connection.host == "127.0.0.1"  # type: ignore[union-attr]
            assert saved.connection.port == port  # type: ignore[union-attr]
        finally:
            await manager.stop_all()

    @pytest.mark.asyncio
    async def test_stop_deletes_saved_machine(self, tmp_path: Path) -> None:
        storage = MachineStorage(tmp_path / "machines")
        manager = SimulatorManager(machine_storage=storage)
        model = _make_model()

        info = await manager.start(model, "test-mfr", port=_find_free_port())
        machine_id = info.machine_id

        await manager.stop(machine_id)

        assert storage.get(machine_id) is None

    @pytest.mark.asyncio
    async def test_auto_port_allocation(self) -> None:
        manager = SimulatorManager()
        model = _make_model()

        info = await manager.start(model, "test-mfr", port=0)
        try:
            assert info.port > 0
        finally:
            await manager.stop_all()

    @pytest.mark.asyncio
    async def test_get_returns_info(self) -> None:
        manager = SimulatorManager()
        model = _make_model()

        info = await manager.start(model, "test-mfr", port=_find_free_port())
        try:
            result = manager.get(info.machine_id)
            assert result is not None
            assert result.machine_id == info.machine_id
        finally:
            await manager.stop_all()

    @pytest.mark.asyncio
    async def test_real_catalog_model(self) -> None:
        """Test with a real catalog model (Stratto 2.0)."""
        model = get_model("carmomaq", "carmomaq-stratto-2.0")
        assert model is not None

        manager = SimulatorManager()
        info = await manager.start(model, "carmomaq", port=_find_free_port())
        try:
            assert info.catalog_id == "carmomaq-stratto-2.0"
            assert "Stratto" in info.name
        finally:
            await manager.stop_all()
