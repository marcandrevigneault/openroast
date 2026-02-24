"""FastAPI application entry point."""

import sys
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse

from openroast import __version__
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
from openroast.core.paths import get_data_root
from openroast.core.schedule_storage import ScheduleStorage
from openroast.core.storage import ProfileStorage
from openroast.simulator.manager import SimulatorManager
from openroast.ws.live import init_manager as init_ws_manager
from openroast.ws.live import router as ws_router

app = FastAPI(
    title="OpenRoast",
    version=__version__,
    description="Browser-based coffee roasting software",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialise file-based storage
_data_root = get_data_root()
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
    return {"status": "ok", "version": __version__}


# ── Static frontend serving (production only) ──────────────────────
# Serve the built SvelteKit frontend when the static directory exists.
# In development this directory is absent, so the block is skipped.

_frontend_dir = Path(__file__).resolve().parent / "static"
if not _frontend_dir.exists():
    _bundle_root = getattr(sys, "_MEIPASS", None)
    if _bundle_root:
        _frontend_dir = Path(_bundle_root) / "static"

if _frontend_dir.exists():
    _fallback_html = _frontend_dir / "index.html"

    @app.middleware("http")
    async def _spa_fallback(request: Request, call_next):  # type: ignore[no-untyped-def]
        """Serve the SPA fallback for non-API routes that return 404."""
        response: Response = await call_next(request)
        path = request.url.path
        if (
            response.status_code == 404
            and not path.startswith("/api")
            and not path.startswith("/ws")
            and _fallback_html.exists()
        ):
            return FileResponse(_fallback_html)
        return response

    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")
