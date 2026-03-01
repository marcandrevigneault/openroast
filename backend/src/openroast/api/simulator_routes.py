"""REST API routes for the machine simulator."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

if TYPE_CHECKING:
    from openroast.simulator.manager import SimulatorManager

logger = logging.getLogger(__name__)

router = APIRouter()

_sim_manager: SimulatorManager | None = None


def init_simulator_manager(manager: SimulatorManager) -> None:
    """Configure the simulator manager for API endpoints."""
    global _sim_manager
    _sim_manager = manager


def _get_sim_manager() -> SimulatorManager:
    if _sim_manager is None:
        raise RuntimeError("SimulatorManager not initialised")
    return _sim_manager


class StartSimulatorRequest(BaseModel):
    """Request body for starting a simulator."""

    manufacturer_id: str
    model_id: str
    port: int = 0
    name: str | None = None


class SimulatorResponse(BaseModel):
    """Response for a running simulator."""

    machine_id: str
    catalog_id: str
    manufacturer_id: str
    name: str
    port: int
    host: str


@router.post("/simulator/start", status_code=201)
async def start_simulator(req: StartSimulatorRequest) -> SimulatorResponse:
    """Start a simulator for a catalog machine.

    Creates a Modbus TCP server and a SavedMachine pointing to it.
    """
    from openroast.catalog.loader import get_model

    manager = _get_sim_manager()
    model = get_model(req.manufacturer_id, req.model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Catalog model not found")

    info = await manager.start(
        model, req.manufacturer_id, port=req.port, name=req.name,
    )

    return SimulatorResponse(
        machine_id=info.machine_id,
        catalog_id=info.catalog_id,
        manufacturer_id=info.manufacturer_id,
        name=info.name,
        port=info.port,
        host=info.host,
    )


@router.post("/simulator/{machine_id}/stop", status_code=204)
async def stop_simulator(machine_id: str) -> None:
    """Stop a running simulator."""
    manager = _get_sim_manager()
    try:
        await manager.stop(machine_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/simulator")
async def list_simulators() -> list[SimulatorResponse]:
    """List all running simulators."""
    manager = _get_sim_manager()
    return [
        SimulatorResponse(
            machine_id=info.machine_id,
            catalog_id=info.catalog_id,
            manufacturer_id=info.manufacturer_id,
            name=info.name,
            port=info.port,
            host=info.host,
        )
        for info in manager.list_running()
    ]
