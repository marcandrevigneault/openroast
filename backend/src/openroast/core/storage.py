"""File-based JSON storage for roast profiles."""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING

from openroast.models.profile import RoastProfile

if TYPE_CHECKING:
    from pathlib import Path


class ProfileStorage:
    """Persists roast profiles as JSON files in a directory.

    Each profile is stored as ``{id}.json`` under ``data_dir``.
    An optional chart image is stored as ``{id}.png``.
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

    def save_image(self, profile_id: str, data: bytes) -> None:
        """Save a chart image (PNG) for a profile."""
        path = self._dir / f"{profile_id}.png"
        path.write_bytes(data)

    def get_image(self, profile_id: str) -> bytes | None:
        """Load a chart image by profile ID, or None if not found."""
        path = self._dir / f"{profile_id}.png"
        if not path.exists():
            return None
        return path.read_bytes()

    def has_image(self, profile_id: str) -> bool:
        """Check whether a chart image exists for a profile."""
        return (self._dir / f"{profile_id}.png").exists()

    def list_all(self) -> list[dict]:
        """Return summary dicts for every stored profile."""
        summaries: list[dict] = []
        for path in sorted(self._dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                profile_id = data.get("id", path.stem)
                summaries.append({
                    "id": profile_id,
                    "name": data.get("name", ""),
                    "machine": data.get("machine", ""),
                    "created_at": data.get("created_at", ""),
                    "bean_name": data.get("bean_name", ""),
                    "data_points": len(data.get("temperatures", [])),
                    "has_image": self.has_image(profile_id),
                })
            except (json.JSONDecodeError, KeyError):
                continue
        return summaries

    def delete(self, profile_id: str) -> bool:
        """Delete a profile by ID. Returns True if deleted."""
        path = self._dir / f"{profile_id}.json"
        if path.exists():
            path.unlink()
            # Also remove the image if it exists
            img_path = self._dir / f"{profile_id}.png"
            if img_path.exists():
                img_path.unlink()
            return True
        return False
