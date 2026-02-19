"""REST API routes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/machines")
async def list_machines() -> list[dict]:
    """List configured roasting machines."""
    return []


@router.get("/profiles")
async def list_profiles() -> list[dict]:
    """List saved roast profiles."""
    return []
