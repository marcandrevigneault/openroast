"""FastAPI application entry point."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from openroast.api.routes import (
    init_machine_storage,
    init_manager,
    init_schedule_storage,
    init_storage,
)
from openroast.api.routes import router as api_router
from openroast.api.simulator_routes import init_simulator_manager
from openroast.api.simulator_routes import router as sim_router
from openroast.core.machine_storage import MachineStorage
from openroast.core.manager import MachineManager
from openroast.core.schedule_storage import ScheduleStorage
from openroast.core.storage import ProfileStorage
from openroast.simulator.manager import SimulatorManager
from openroast.ws.live import init_manager as init_ws_manager
from openroast.ws.live import router as ws_router

app = FastAPI(
    title="OpenRoast",
    version="0.1.0",
    description="Browser-based coffee roasting software",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialise file-based storage
_data_root = Path(__file__).resolve().parent.parent.parent / "data"
_machine_storage = MachineStorage(_data_root / "machines")

init_storage(ProfileStorage(_data_root / "profiles"))
init_machine_storage(_machine_storage)
init_schedule_storage(ScheduleStorage(_data_root / "schedules"))

# Initialise machine manager and share with routes + WebSocket handler
_manager = MachineManager(_machine_storage)
init_manager(_manager)
init_ws_manager(_manager)

# Initialise simulator manager
_sim_manager = SimulatorManager(_machine_storage)
init_simulator_manager(_sim_manager)

app.include_router(api_router, prefix="/api")
app.include_router(sim_router, prefix="/api")
app.include_router(ws_router, prefix="/ws")


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
