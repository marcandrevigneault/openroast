"""Unit tests for REST API routes."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from openroast.main import app


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
