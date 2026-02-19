"""Unit tests for REST API routes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path
from httpx import ASGITransport, AsyncClient

from openroast.api.routes import init_storage
from openroast.core.storage import ProfileStorage
from openroast.main import app


@pytest.fixture(autouse=True)
def _setup_storage(tmp_path: Path) -> None:
    """Use a temp directory for profile storage in all tests."""
    init_storage(ProfileStorage(tmp_path / "profiles"))


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealthEndpoint:
    async def test_health_returns_ok(self, client: AsyncClient) -> None:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestMachinesEndpoint:
    async def test_list_machines_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/machines")
        assert resp.status_code == 200
        assert resp.json() == []


class TestProfilesEndpoint:
    async def test_list_profiles_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/profiles")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_save_profile(self, client: AsyncClient) -> None:
        payload = {
            "profile": {
                "name": "Test Roast",
                "machine": "Stratto",
                "temperatures": [
                    {"timestamp_ms": 0, "et": 210, "bt": 155},
                    {"timestamp_ms": 3000, "et": 212, "bt": 160, "et_ror": 5.0, "bt_ror": 8.0},
                ],
                "events": [{"event_type": "CHARGE", "timestamp_ms": 0}],
                "controls": {"burner": [[0, 50], [3000, 75]]},
            },
            "bean_name": "Ethiopian",
            "bean_weight_g": 500,
        }
        resp = await client.post("/api/profiles", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body

    async def test_list_after_save(self, client: AsyncClient) -> None:
        payload = {
            "profile": {
                "name": "Roast A",
                "temperatures": [{"timestamp_ms": 0, "et": 200, "bt": 150}],
            }
        }
        await client.post("/api/profiles", json=payload)
        resp = await client.get("/api/profiles")
        assert resp.status_code == 200
        profiles = resp.json()
        assert len(profiles) == 1
        assert profiles[0]["name"] == "Roast A"

    async def test_get_profile(self, client: AsyncClient) -> None:
        payload = {
            "profile": {
                "name": "My Roast",
                "machine": "Stratto",
                "temperatures": [{"timestamp_ms": 0, "et": 210, "bt": 155}],
            }
        }
        save_resp = await client.post("/api/profiles", json=payload)
        profile_id = save_resp.json()["id"]

        resp = await client.get(f"/api/profiles/{profile_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "My Roast"
        assert len(body["temperatures"]) == 1

    async def test_get_nonexistent_profile(self, client: AsyncClient) -> None:
        resp = await client.get("/api/profiles/nonexistent")
        assert resp.status_code == 404

    async def test_delete_profile(self, client: AsyncClient) -> None:
        payload = {
            "profile": {
                "name": "Delete Me",
                "temperatures": [{"timestamp_ms": 0, "et": 200, "bt": 150}],
            }
        }
        save_resp = await client.post("/api/profiles", json=payload)
        profile_id = save_resp.json()["id"]

        resp = await client.delete(f"/api/profiles/{profile_id}")
        assert resp.status_code == 204

        # Verify it's gone
        resp = await client.get(f"/api/profiles/{profile_id}")
        assert resp.status_code == 404

    async def test_delete_nonexistent_profile(self, client: AsyncClient) -> None:
        resp = await client.delete("/api/profiles/nonexistent")
        assert resp.status_code == 404

    async def test_save_with_name_override(self, client: AsyncClient) -> None:
        payload = {
            "profile": {
                "name": "Original",
                "temperatures": [{"timestamp_ms": 0, "et": 200, "bt": 150}],
            },
            "name": "Override Name",
        }
        save_resp = await client.post("/api/profiles", json=payload)
        profile_id = save_resp.json()["id"]

        resp = await client.get(f"/api/profiles/{profile_id}")
        assert resp.json()["name"] == "Override Name"
