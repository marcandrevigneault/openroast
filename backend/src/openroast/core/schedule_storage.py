"""File-based JSON storage for roast schedules."""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

from openroast.models.schedule import SavedSchedule

if TYPE_CHECKING:
    from pathlib import Path


class ScheduleStorage:
    """Persists roast schedules as JSON files in a directory.

    Each schedule is stored as ``{id}.json`` under ``data_dir``.
    """

    def __init__(self, data_dir: Path) -> None:
        self._dir = data_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, schedule: SavedSchedule) -> str:
        """Save a schedule and return its ID."""
        schedule_id = schedule.id or str(uuid.uuid4())
        schedule.id = schedule_id
        path = self._dir / f"{schedule_id}.json"
        path.write_text(schedule.model_dump_json(indent=2), encoding="utf-8")
        return schedule_id

    def get(self, schedule_id: str) -> SavedSchedule | None:
        """Load a schedule by ID, or None if not found."""
        path = self._dir / f"{schedule_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return SavedSchedule.model_validate(data)

    def list_all(self) -> list[dict]:
        """Return summary dicts for every stored schedule."""
        summaries: list[dict] = []
        for path in sorted(self._dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                summaries.append({
                    "id": data.get("id", path.stem),
                    "name": data.get("name", ""),
                    "machine_name": data.get("machine_name", ""),
                    "created_at": data.get("created_at", ""),
                    "step_count": len(data.get("steps", [])),
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return summaries

    def delete(self, schedule_id: str) -> bool:
        """Delete a schedule by ID. Returns True if deleted."""
        path = self._dir / f"{schedule_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False
