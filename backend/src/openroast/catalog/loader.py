"""Machine catalog loader.

Loads the static machine catalog from the bundled JSON file and provides
lookup functions for manufacturers and models.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import TYPE_CHECKING

from openroast.models.catalog import CatalogManufacturer, CatalogModel, MachineCatalog

if TYPE_CHECKING:
    from pathlib import Path

_CATALOG_PATH: Path | None = None


def _default_catalog_path() -> Path:
    from pathlib import Path

    from openroast.core.paths import get_bundle_root

    bundle = get_bundle_root()
    if bundle is not None:
        return bundle / "openroast" / "catalog" / "machines.json"
    return Path(__file__).parent / "machines.json"


@lru_cache(maxsize=1)
def load_catalog() -> MachineCatalog:
    """Load and validate the machine catalog from disk."""
    path = _CATALOG_PATH or _default_catalog_path()
    data = json.loads(path.read_text(encoding="utf-8"))
    return MachineCatalog.model_validate(data)


def get_manufacturers() -> list[CatalogManufacturer]:
    """Return all manufacturers in the catalog."""
    return load_catalog().manufacturers


def get_manufacturer(manufacturer_id: str) -> CatalogManufacturer | None:
    """Look up a manufacturer by ID."""
    for m in load_catalog().manufacturers:
        if m.id == manufacturer_id:
            return m
    return None


def get_model(manufacturer_id: str, model_id: str) -> CatalogModel | None:
    """Look up a specific model by manufacturer and model ID."""
    manufacturer = get_manufacturer(manufacturer_id)
    if manufacturer is None:
        return None
    for model in manufacturer.models:
        if model.id == model_id:
            return model
    return None
