"""REST API routes."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from openroast.models.machine import SavedMachine
from openroast.models.profile import RoastProfile  # noqa: TC001
from openroast.models.schedule import SavedSchedule  # noqa: TC001

if TYPE_CHECKING:
    from openroast.core.machine_storage import MachineStorage
    from openroast.core.manager import MachineManager
    from openroast.core.schedule_storage import ScheduleStorage
    from openroast.core.storage import ProfileStorage

logger = logging.getLogger(__name__)

router = APIRouter()

# Storage instances — set by init_*() at startup
_storage: ProfileStorage | None = None
_machine_storage: MachineStorage | None = None
_schedule_storage: ScheduleStorage | None = None
_manager: MachineManager | None = None


def init_storage(storage: ProfileStorage) -> None:
    """Configure the profile storage backend."""
    global _storage
    _storage = storage


def init_machine_storage(storage: MachineStorage) -> None:
    """Configure the machine storage backend."""
    global _machine_storage
    _machine_storage = storage


def init_schedule_storage(storage: ScheduleStorage) -> None:
    """Configure the schedule storage backend."""
    global _schedule_storage
    _schedule_storage = storage


def init_manager(manager: MachineManager) -> None:
    """Configure the machine manager for REST endpoints."""
    global _manager
    _manager = manager


def _get_storage() -> ProfileStorage:
    if _storage is None:
        raise RuntimeError("Storage not initialised")
    return _storage


def _get_machine_storage() -> MachineStorage:
    if _machine_storage is None:
        raise RuntimeError("Machine storage not initialised")
    return _machine_storage


def _get_schedule_storage() -> ScheduleStorage:
    if _schedule_storage is None:
        raise RuntimeError("Schedule storage not initialised")
    return _schedule_storage


def _get_manager() -> MachineManager:
    if _manager is None:
        raise RuntimeError("MachineManager not initialised")
    return _manager


# --- Catalog (read-only) ---


@router.get("/catalog/manufacturers")
async def list_manufacturers() -> list[dict]:
    """List all manufacturers from the static catalog."""
    from openroast.catalog.loader import get_manufacturers

    return [
        {"id": m.id, "name": m.name, "country": m.country, "model_count": len(m.models)}
        for m in get_manufacturers()
    ]


@router.get("/catalog/manufacturers/{manufacturer_id}/models")
async def list_manufacturer_models(manufacturer_id: str) -> list[dict]:
    """List models for a specific manufacturer."""
    from openroast.catalog.loader import get_manufacturer

    mfr = get_manufacturer(manufacturer_id)
    if mfr is None:
        raise HTTPException(status_code=404, detail="Manufacturer not found")
    return [m.model_dump() for m in mfr.models]


@router.get("/catalog/manufacturers/{manufacturer_id}/models/{model_id}")
async def get_catalog_model(manufacturer_id: str, model_id: str) -> dict:
    """Get a specific catalog model."""
    from openroast.catalog.loader import get_model

    model = get_model(manufacturer_id, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return model.model_dump()


# --- Machines CRUD ---


class CreateMachineFromCatalogRequest(BaseModel):
    """Request body for creating a machine from a catalog entry."""

    manufacturer_id: str
    model_id: str
    name: str | None = None


@router.get("/machines")
async def list_machines() -> list[dict]:
    """List saved machine configurations."""
    storage = _get_machine_storage()
    return storage.list_all()


@router.post("/machines", status_code=201)
async def create_machine(machine: SavedMachine) -> dict:
    """Save a new machine configuration."""
    storage = _get_machine_storage()
    machine_id = storage.save(machine)
    return {"id": machine_id}


@router.post("/machines/from-catalog", status_code=201)
async def create_machine_from_catalog(req: CreateMachineFromCatalogRequest) -> dict:
    """Create a machine from a catalog entry with default settings."""
    from openroast.catalog.loader import get_model

    model = get_model(req.manufacturer_id, req.model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Catalog model not found")

    machine = SavedMachine(
        name=req.name or model.name,
        catalog_manufacturer_id=req.manufacturer_id,
        catalog_model_id=req.model_id,
        protocol=model.protocol,
        connection=model.connection,
        sampling_interval_ms=model.sampling_interval_ms,
        et=model.et,
        bt=model.bt,
        extra_channels=model.extra_channels,
        controls=model.controls,
    )
    storage = _get_machine_storage()
    machine_id = storage.save(machine)
    return {"id": machine_id, "machine": machine.model_dump()}


@router.get("/machines/{machine_id}")
async def get_machine(machine_id: str) -> SavedMachine:
    """Get a saved machine by ID."""
    storage = _get_machine_storage()
    machine = storage.get(machine_id)
    if machine is None:
        raise HTTPException(status_code=404, detail="Machine not found")
    return machine


@router.put("/machines/{machine_id}")
async def update_machine(machine_id: str, machine: SavedMachine) -> SavedMachine:
    """Update a saved machine configuration."""
    storage = _get_machine_storage()
    existing = storage.get(machine_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Machine not found")
    machine.id = machine_id
    storage.save(machine)
    return machine


@router.delete("/machines/{machine_id}", status_code=204)
async def delete_machine(machine_id: str) -> None:
    """Delete a saved machine."""
    storage = _get_machine_storage()
    if not storage.delete(machine_id):
        raise HTTPException(status_code=404, detail="Machine not found")


# --- Machine Connection ---


@router.post("/machines/{machine_id}/connect")
async def connect_machine(machine_id: str) -> dict:
    """Connect to a machine (load driver, start sampling).

    The machine must exist in storage. Once connected, WebSocket clients
    can subscribe to /ws/live/{machine_id} for real-time data.
    """
    manager = _get_manager()
    try:
        await manager.connect_machine(machine_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ConnectionError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return {"status": "connected", "machine_id": machine_id}


@router.post("/machines/{machine_id}/disconnect")
async def disconnect_machine(machine_id: str) -> dict:
    """Disconnect a machine (stop sampling, release driver)."""
    manager = _get_manager()
    await manager.disconnect_machine(machine_id)
    return {"status": "disconnected", "machine_id": machine_id}


@router.get("/machines/{machine_id}/status")
async def machine_status(machine_id: str) -> dict:
    """Get the current connection and session status of a machine."""
    manager = _get_manager()
    instance = manager.get_instance(machine_id)
    if instance is None:
        return {
            "machine_id": machine_id,
            "connected": False,
            "driver_state": "disconnected",
            "session_state": "idle",
        }
    return {
        "machine_id": machine_id,
        "connected": True,
        "driver_state": instance.driver.state.value,
        "session_state": instance.session.state.value,
    }


# --- Profiles CRUD ---


class SaveProfileRequest(BaseModel):
    """Request body for saving a profile."""

    profile: RoastProfile
    name: str | None = None
    bean_name: str | None = None
    bean_weight_g: float | None = None


@router.post("/profiles", status_code=201)
async def save_profile(req: SaveProfileRequest) -> dict:
    """Save a roast profile."""
    storage = _get_storage()
    profile = req.profile
    if req.name:
        profile.name = req.name
    if req.bean_name is not None:
        profile.bean_name = req.bean_name
    if req.bean_weight_g is not None:
        profile.bean_weight_g = req.bean_weight_g
    profile_id = storage.save(profile)
    return {"id": profile_id}


@router.get("/profiles")
async def list_profiles() -> list[dict]:
    """List saved roast profiles."""
    storage = _get_storage()
    return storage.list_all()


@router.get("/profiles/{profile_id}")
async def get_profile(profile_id: str) -> RoastProfile:
    """Get a single profile by ID."""
    storage = _get_storage()
    profile = storage.get(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.delete("/profiles/{profile_id}", status_code=204)
async def delete_profile(profile_id: str) -> None:
    """Delete a profile."""
    storage = _get_storage()
    if not storage.delete(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")


# --- Schedules CRUD ---


@router.post("/schedules", status_code=201)
async def save_schedule(schedule: SavedSchedule) -> dict:
    """Save a roast schedule."""
    storage = _get_schedule_storage()
    schedule_id = storage.save(schedule)
    return {"id": schedule_id}


@router.get("/schedules")
async def list_schedules() -> list[dict]:
    """List saved roast schedules."""
    storage = _get_schedule_storage()
    return storage.list_all()


@router.get("/schedules/{schedule_id}")
async def get_schedule(schedule_id: str) -> SavedSchedule:
    """Get a single schedule by ID."""
    storage = _get_schedule_storage()
    schedule = storage.get(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_schedule(schedule_id: str) -> None:
    """Delete a schedule."""
    storage = _get_schedule_storage()
    if not storage.delete(schedule_id):
        raise HTTPException(status_code=404, detail="Schedule not found")
