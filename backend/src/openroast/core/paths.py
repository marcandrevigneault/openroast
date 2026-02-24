"""Application data paths.

Resolves the data root directory based on the runtime environment:
- Development: ``backend/data/`` (relative to source tree)
- Packaged app: ``~/Library/Application Support/OpenRoast/``
"""

from __future__ import annotations

import sys
from pathlib import Path


def is_bundled() -> bool:
    """Return True if running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def get_data_root() -> Path:
    """Return the root directory for user data.

    In development, this is the ``data/`` directory in the backend source tree.
    In a packaged app, this is ``~/Library/Application Support/OpenRoast/``.
    """
    if is_bundled():
        return Path.home() / "Library" / "Application Support" / "OpenRoast"
    return Path(__file__).resolve().parent.parent.parent / "data"


def get_bundle_root() -> Path | None:
    """Return the PyInstaller bundle root, or None in dev."""
    if is_bundled():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return None
