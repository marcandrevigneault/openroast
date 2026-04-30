"""File-based JSON storage for machine configurations.

Each machine config is stored as ``{id}.json`` under a ``machines/``
directory.  Follows the same pattern as :class:`ProfileStorage`.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from openroast.catalog.loader import get_model
from openroast.models.machine import SavedMachine

if TYPE_CHECKING:
    from pathlib import Path

    from openroast.models.catalog import CatalogModel, ControlConfig

logger = logging.getLogger(__name__)


def _migrate_from_catalog(machine: SavedMachine) -> SavedMachine:
    """Upgrade a saved machine in-place against its source catalog model.

    Older machines saved before features like ON/OFF toggles existed are
    missing the corresponding control entries.  Without this migration
    the runtime driver has no toggle commands to write or registers to
    poll, so the v1.6+ readback feature appears broken.

    The migration is conservative:
      * keeps user customisations like host/port/sampling_interval_ms,
      * adds catalog controls that are absent in the saved machine,
      * for sliders present in both, copies the catalog ``toggle`` config
        only if the saved one is missing it.
    """
    if not (machine.catalog_manufacturer_id and machine.catalog_model_id):
        return machine
    catalog: CatalogModel | None = get_model(
        machine.catalog_manufacturer_id, machine.catalog_model_id,
    )
    if catalog is None:
        return machine

    saved_by_channel: dict[str, ControlConfig] = {
        c.channel: c for c in machine.controls
    }
    merged: list[ControlConfig] = []
    changed = False
    for cat_ctrl in catalog.controls:
        existing = saved_by_channel.get(cat_ctrl.channel)
        if existing is None:
            merged.append(cat_ctrl)
            changed = True
            logger.info(
                "Catalog migration on %s: added missing control %s",
                machine.id, cat_ctrl.channel,
            )
        else:
            if cat_ctrl.toggle and existing.toggle is None:
                existing = existing.model_copy(update={"toggle": cat_ctrl.toggle})
                changed = True
                logger.info(
                    "Catalog migration on %s: added missing toggle to %s",
                    machine.id, existing.channel,
                )
            merged.append(existing)
    if not changed:
        return machine
    return machine.model_copy(update={"controls": merged})


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
        """Load a machine by ID, applying catalog migrations on the fly."""
        path = self._dir / f"{machine_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        machine = SavedMachine.model_validate(data)
        migrated = _migrate_from_catalog(machine)
        if migrated is not machine:
            # Persist so the migration is one-shot per machine.
            self.save(migrated)
        return migrated

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
