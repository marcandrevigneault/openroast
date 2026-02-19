"""File-based JSON storage for roast profiles."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from openroast.models.profile import RoastProfile


class ProfileStorage:
    """Persists roast profiles as JSON files in a directory.

    Each profile is stored as ``{id}.json`` under ``data_dir``.
    """

    def __init__(self, data_dir: Path) -> None:
        self._dir = data_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, profile: RoastProfile) -> str:
        """Save a profile and return its ID."""
        profile_id = profile.id or str(uuid.uuid4())
        profile.id = profile_id
        path = self._dir / f"{profile_id}.json"
        path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
        return profile_id

    def get(self, profile_id: str) -> RoastProfile | None:
        """Load a profile by ID, or None if not found."""
        path = self._dir / f"{profile_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return RoastProfile.model_validate(data)

    def list_all(self) -> list[dict]:
        """Return summary dicts for every stored profile."""
        summaries: list[dict] = []
        for path in sorted(self._dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                summaries.append({
                    "id": data.get("id", path.stem),
                    "name": data.get("name", ""),
                    "machine": data.get("machine", ""),
                    "created_at": data.get("created_at", ""),
                    "bean_name": data.get("bean_name", ""),
                    "data_points": len(data.get("temperatures", [])),
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return summaries

    def delete(self, profile_id: str) -> bool:
        """Delete a profile by ID. Returns True if deleted."""
        path = self._dir / f"{profile_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False
