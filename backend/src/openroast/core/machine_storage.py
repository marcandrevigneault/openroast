"""File-based JSON storage for machine configurations.

Each machine config is stored as ``{id}.json`` under a ``machines/``
directory.  Follows the same pattern as :class:`ProfileStorage`.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from openroast.models.machine import SavedMachine

if TYPE_CHECKING:
    from pathlib import Path


class MachineStorage:
    """Persists machine configurations as JSON files."""

    def __init__(self, data_dir: Path) -> None:
        self._dir = data_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, machine: SavedMachine) -> str:
        """Save a machine config and return its ID."""
        path = self._dir / f"{machine.id}.json"
        path.write_text(machine.model_dump_json(indent=2), encoding="utf-8")
        return machine.id

    def get(self, machine_id: str) -> SavedMachine | None:
        """Load a machine by ID."""
        path = self._dir / f"{machine_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return SavedMachine.model_validate(data)

    def list_all(self) -> list[dict]:
        """Return summaries of all saved machines."""
        summaries: list[dict] = []
        for path in sorted(self._dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                machine = SavedMachine.model_validate(data)
                summaries.append({
                    "id": machine.id,
                    "name": machine.name,
                    "protocol": machine.protocol,
                    "catalog_manufacturer_id": machine.catalog_manufacturer_id,
                    "catalog_model_id": machine.catalog_model_id,
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return summaries

    def delete(self, machine_id: str) -> bool:
        """Delete a machine by ID."""
        path = self._dir / f"{machine_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False
