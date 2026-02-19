"""Unit tests for simulator API routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient

from openroast.api.routes import init_machine_storage, init_manager, init_storage
from openroast.api.simulator_routes import init_simulator_manager
from openroast.core.machine_storage import MachineStorage
from openroast.core.manager import MachineManager
from openroast.core.storage import ProfileStorage
from openroast.main import app
from openroast.simulator.manager import SimulatorManager

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture(autouse=True)
def _setup_storage(tmp_path: Path) -> None:
    """Use a temp directory for storage in all tests."""
    storage = MachineStorage(tmp_path / "machines")
    init_storage(ProfileStorage(tmp_path / "profiles"))
    init_machine_storage(storage)
    init_manager(MachineManager(storage))
    init_simulator_manager(SimulatorManager(storage))


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestStartSimulator:
    async def test_start_simulator(self, client: AsyncClient) -> None:
        resp = await client.post("/api/simulator/start", json={
            "manufacturer_id": "carmomaq",
            "model_id": "carmomaq-stratto-2.0",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["catalog_id"] == "carmomaq-stratto-2.0"
        assert data["port"] > 0
        assert "Stratto" in data["name"]
        assert data["machine_id"]

        # Cleanup
        await client.post(f"/api/simulator/{data['machine_id']}/stop")

    async def test_start_with_custom_port(self, client: AsyncClient) -> None:
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

        resp = await client.post("/api/simulator/start", json={
            "manufacturer_id": "carmomaq",
            "model_id": "carmomaq-stratto-2.0",
            "port": port,
        })
        assert resp.status_code == 201
        assert resp.json()["port"] == port

        await client.post(f"/api/simulator/{resp.json()['machine_id']}/stop")

    async def test_start_nonexistent_model_returns_404(self, client: AsyncClient) -> None:
        resp = await client.post("/api/simulator/start", json={
            "manufacturer_id": "nonexistent",
            "model_id": "nonexistent",
        })
        assert resp.status_code == 404

    async def test_start_duplicate_returns_409(self, client: AsyncClient) -> None:
        resp1 = await client.post("/api/simulator/start", json={
            "manufacturer_id": "carmomaq",
            "model_id": "carmomaq-stratto-2.0",
        })
        assert resp1.status_code == 201

        resp2 = await client.post("/api/simulator/start", json={
            "manufacturer_id": "carmomaq",
            "model_id": "carmomaq-stratto-2.0",
        })
        assert resp2.status_code == 409

        await client.post(f"/api/simulator/{resp1.json()['machine_id']}/stop")


class TestStopSimulator:
    async def test_stop_simulator(self, client: AsyncClient) -> None:
        resp = await client.post("/api/simulator/start", json={
            "manufacturer_id": "carmomaq",
            "model_id": "carmomaq-stratto-2.0",
        })
        machine_id = resp.json()["machine_id"]

        resp = await client.post(f"/api/simulator/{machine_id}/stop")
        assert resp.status_code == 204

    async def test_stop_nonexistent_returns_404(self, client: AsyncClient) -> None:
        resp = await client.post("/api/simulator/nonexistent/stop")
        assert resp.status_code == 404


class TestListSimulators:
    async def test_list_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/simulator")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_list_running(self, client: AsyncClient) -> None:
        resp = await client.post("/api/simulator/start", json={
            "manufacturer_id": "carmomaq",
            "model_id": "carmomaq-stratto-2.0",
        })
        machine_id = resp.json()["machine_id"]

        resp = await client.get("/api/simulator")
        assert resp.status_code == 200
        sims = resp.json()
        assert len(sims) == 1
        assert sims[0]["catalog_id"] == "carmomaq-stratto-2.0"

        await client.post(f"/api/simulator/{machine_id}/stop")
