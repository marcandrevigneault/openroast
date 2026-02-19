"""FastAPI application entry point."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from openroast.api.routes import init_storage, router as api_router
from openroast.core.storage import ProfileStorage
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

# Initialise file-based profile storage
_data_dir = Path(__file__).resolve().parent.parent.parent / "data" / "profiles"
init_storage(ProfileStorage(_data_dir))

app.include_router(api_router, prefix="/api")
app.include_router(ws_router, prefix="/ws")


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}
