"""Unit tests for MachineStorage."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from openroast.core.machine_storage import MachineStorage
from openroast.models.catalog import (
    ControlConfig,
    ModbusConnectionConfig,
    ProtocolType,
    SerialConnectionConfig,
)
from openroast.models.machine import SavedMachine

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def storage(tmp_path: Path) -> MachineStorage:
    return MachineStorage(tmp_path / "machines")


def _make_machine(name: str = "Test Machine") -> SavedMachine:
    return SavedMachine(
        name=name,
        protocol=ProtocolType.MODBUS_TCP,
        connection=ModbusConnectionConfig(host="192.168.1.1"),
        controls=[ControlConfig(name="Burner", channel="burner")],
    )


class TestSaveAndGet:
    def test_save_returns_id(self, storage: MachineStorage) -> None:
        machine_id = storage.save(_make_machine())
        assert isinstance(machine_id, str)
        assert len(machine_id) > 0

    def test_get_returns_saved_machine(self, storage: MachineStorage) -> None:
        machine = _make_machine("My Roaster")
        machine_id = storage.save(machine)
        loaded = storage.get(machine_id)
        assert loaded is not None
        assert loaded.name == "My Roaster"
        assert loaded.protocol == ProtocolType.MODBUS_TCP

    def test_get_preserves_connection(self, storage: MachineStorage) -> None:
        machine = _make_machine()
        machine_id = storage.save(machine)
        loaded = storage.get(machine_id)
        assert loaded is not None
        assert loaded.connection.type == "modbus_tcp"
        assert loaded.connection.host == "192.168.1.1"  # type: ignore[union-attr]

    def test_get_preserves_controls(self, storage: MachineStorage) -> None:
        machine = _make_machine()
        machine_id = storage.save(machine)
        loaded = storage.get(machine_id)
        assert loaded is not None
        assert len(loaded.controls) == 1
        assert loaded.controls[0].name == "Burner"

    def test_get_nonexistent_returns_none(self, storage: MachineStorage) -> None:
        assert storage.get("nonexistent") is None

    def test_save_with_explicit_id(self, storage: MachineStorage) -> None:
        machine = _make_machine()
        machine.id = "custom-id"
        machine_id = storage.save(machine)
        assert machine_id == "custom-id"
        loaded = storage.get("custom-id")
        assert loaded is not None
        assert loaded.id == "custom-id"


class TestListAll:
    def test_empty_storage(self, storage: MachineStorage) -> None:
        assert storage.list_all() == []

    def test_lists_saved_machines(self, storage: MachineStorage) -> None:
        storage.save(_make_machine("Roaster A"))
        storage.save(_make_machine("Roaster B"))
        summaries = storage.list_all()
        assert len(summaries) == 2
        names = {s["name"] for s in summaries}
        assert "Roaster A" in names
        assert "Roaster B" in names

    def test_summary_has_expected_fields(self, storage: MachineStorage) -> None:
        storage.save(_make_machine())
        summary = storage.list_all()[0]
        assert "id" in summary
        assert "name" in summary
        assert "protocol" in summary


class TestDelete:
    def test_delete_existing(self, storage: MachineStorage) -> None:
        machine_id = storage.save(_make_machine())
        assert storage.delete(machine_id) is True
        assert storage.get(machine_id) is None

    def test_delete_nonexistent(self, storage: MachineStorage) -> None:
        assert storage.delete("nonexistent") is False


class TestDifferentProtocols:
    def test_serial_machine(self, storage: MachineStorage) -> None:
        machine = SavedMachine(
            name="Serial Machine",
            protocol=ProtocolType.SERIAL,
            connection=SerialConnectionConfig(comport="/dev/ttyUSB0"),
        )
        machine_id = storage.save(machine)
        loaded = storage.get(machine_id)
        assert loaded is not None
        assert loaded.connection.type == "serial"
        assert loaded.connection.comport == "/dev/ttyUSB0"  # type: ignore[union-attr]
