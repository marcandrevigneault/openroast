"""REST API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from openroast.core.storage import ProfileStorage
from openroast.models.profile import RoastProfile

router = APIRouter()

# Storage instance — set by init_storage() at startup
_storage: ProfileStorage | None = None


def init_storage(storage: ProfileStorage) -> None:
    """Configure the profile storage backend."""
    global _storage  # noqa: PLW0603
    _storage = storage


def _get_storage() -> ProfileStorage:
    if _storage is None:
        raise RuntimeError("Storage not initialised")
    return _storage


# --- Machines (stub) ---

@router.get("/machines")
async def list_machines() -> list[dict]:
    """List configured roasting machines."""
    return []


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
