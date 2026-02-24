"""Application data paths.

Resolves the data root directory based on the runtime environment:
- Development: ``backend/data/`` (relative to source tree)
- Packaged app (macOS): ``~/Library/Application Support/OpenRoast/``
- Packaged app (Windows): ``%LOCALAPPDATA%/OpenRoast/``
- Packaged app (Linux): ``~/.local/share/openroast/``
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def is_bundled() -> bool:
    """Return True if running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_data_root() -> Path:
    """Return the root directory for user data.

    In development, this is the ``data/`` directory in the backend source tree.
    In a packaged app, the platform-appropriate user data directory is used.
    """
    if is_bundled():
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
            return Path(base) / "OpenRoast"
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "OpenRoast"
        return Path.home() / ".local" / "share" / "openroast"
    return Path(__file__).resolve().parent.parent.parent / "data"


def get_bundle_root() -> Path | None:
    """Return the PyInstaller bundle root, or None in dev."""
    if is_bundled():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return None
