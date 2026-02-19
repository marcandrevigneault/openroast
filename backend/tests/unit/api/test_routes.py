"""Unit tests for REST API routes."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

if TYPE_CHECKING:
    from pathlib import Path
from httpx import ASGITransport, AsyncClient

from openroast.api.routes import init_machine_storage, init_manager, init_storage
from openroast.core.machine_storage import MachineStorage
from openroast.core.manager import MachineManager
from openroast.core.storage import ProfileStorage
from openroast.main import app


@pytest.fixture(autouse=True)
def _setup_storage(tmp_path: Path) -> None:
    """Use a temp directory for storage in all tests."""
    storage = MachineStorage(tmp_path / "machines")
    init_storage(ProfileStorage(tmp_path / "profiles"))
    init_machine_storage(storage)
    init_manager(MachineManager(storage))


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


# --- Catalog endpoints ---


class TestCatalogEndpoints:
    async def test_list_manufacturers(self, client: AsyncClient) -> None:
        resp = await client.get("/api/catalog/manufacturers")
        assert resp.status_code == 200
        mfrs = resp.json()
        assert isinstance(mfrs, list)
        assert len(mfrs) > 0
        ids = {m["id"] for m in mfrs}
        assert "carmomaq" in ids
        assert "giesen" in ids

    async def test_manufacturer_has_model_count(self, client: AsyncClient) -> None:
        resp = await client.get("/api/catalog/manufacturers")
        mfr = next(m for m in resp.json() if m["id"] == "carmomaq")
        assert "model_count" in mfr
        assert mfr["model_count"] >= 1

    async def test_list_models(self, client: AsyncClient) -> None:
        resp = await client.get("/api/catalog/manufacturers/carmomaq/models")
        assert resp.status_code == 200
        models = resp.json()
        assert len(models) >= 1
        ids = {m["id"] for m in models}
        assert "carmomaq-stratto-2.0" in ids

    async def test_list_models_nonexistent_manufacturer(self, client: AsyncClient) -> None:
        resp = await client.get("/api/catalog/manufacturers/nonexistent/models")
        assert resp.status_code == 404

    async def test_get_model(self, client: AsyncClient) -> None:
        resp = await client.get("/api/catalog/manufacturers/carmomaq/models/carmomaq-stratto-2.0")
        assert resp.status_code == 200
        model = resp.json()
        assert model["name"] == "Stratto 2.0"
        assert model["protocol"] == "modbus_tcp"

    async def test_get_model_nonexistent(self, client: AsyncClient) -> None:
        resp = await client.get("/api/catalog/manufacturers/carmomaq/models/nonexistent")
        assert resp.status_code == 404


# --- Machines CRUD ---


class TestMachinesEndpoint:
    async def test_list_machines_empty(self, client: AsyncClient) -> None:
        resp = await client.get("/api/machines")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_machine(self, client: AsyncClient) -> None:
        payload = {
            "name": "My Stratto",
            "protocol": "modbus_tcp",
            "connection": {
                "type": "modbus_tcp",
                "host": "192.168.5.11",
                "port": 502,
            },
        }
        resp = await client.post("/api/machines", json=payload)
        assert resp.status_code == 201
        assert "id" in resp.json()

    async def test_get_machine(self, client: AsyncClient) -> None:
        payload = {
            "name": "My Stratto",
            "protocol": "modbus_tcp",
            "connection": {
                "type": "modbus_tcp",
                "host": "192.168.5.11",
                "port": 502,
            },
        }
        create_resp = await client.post("/api/machines", json=payload)
        machine_id = create_resp.json()["id"]

        resp = await client.get(f"/api/machines/{machine_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "My Stratto"

    async def test_get_nonexistent_machine(self, client: AsyncClient) -> None:
        resp = await client.get("/api/machines/nonexistent")
        assert resp.status_code == 404

    async def test_delete_machine(self, client: AsyncClient) -> None:
        payload = {
            "name": "Delete Me",
            "protocol": "serial",
            "connection": {"type": "serial", "comport": "/dev/ttyUSB0"},
        }
        create_resp = await client.post("/api/machines", json=payload)
        machine_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/machines/{machine_id}")
        assert resp.status_code == 204

        resp = await client.get(f"/api/machines/{machine_id}")
        assert resp.status_code == 404

    async def test_delete_nonexistent_machine(self, client: AsyncClient) -> None:
        resp = await client.delete("/api/machines/nonexistent")
        assert resp.status_code == 404

    async def test_list_after_create(self, client: AsyncClient) -> None:
        payload = {
            "name": "Listed Machine",
            "protocol": "modbus_tcp",
            "connection": {"type": "modbus_tcp"},
        }
        await client.post("/api/machines", json=payload)
        resp = await client.get("/api/machines")
        machines = resp.json()
        assert len(machines) == 1
        assert machines[0]["name"] == "Listed Machine"

    async def test_update_machine(self, client: AsyncClient) -> None:
        payload = {
            "name": "Original",
            "protocol": "modbus_tcp",
            "connection": {"type": "modbus_tcp", "host": "10.0.0.1"},
        }
        create_resp = await client.post("/api/machines", json=payload)
        machine_id = create_resp.json()["id"]

        update_payload = {
            "id": machine_id,
            "name": "Updated",
            "protocol": "modbus_tcp",
            "connection": {"type": "modbus_tcp", "host": "10.0.0.2"},
        }
        resp = await client.put(f"/api/machines/{machine_id}", json=update_payload)
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

        # Verify persisted
        resp = await client.get(f"/api/machines/{machine_id}")
        assert resp.json()["connection"]["host"] == "10.0.0.2"

    async def test_update_nonexistent_machine(self, client: AsyncClient) -> None:
        payload = {
            "name": "Ghost",
            "protocol": "serial",
            "connection": {"type": "serial"},
        }
        resp = await client.put("/api/machines/nonexistent", json=payload)
        assert resp.status_code == 404


class TestCreateFromCatalog:
    async def test_create_from_catalog(self, client: AsyncClient) -> None:
        payload = {
            "manufacturer_id": "carmomaq",
            "model_id": "carmomaq-stratto-2.0",
            "name": "My Stratto",
        }
        resp = await client.post("/api/machines/from-catalog", json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert body["machine"]["name"] == "My Stratto"
        assert body["machine"]["protocol"] == "modbus_tcp"
        assert body["machine"]["catalog_manufacturer_id"] == "carmomaq"

    async def test_create_from_catalog_default_name(self, client: AsyncClient) -> None:
        payload = {
            "manufacturer_id": "giesen",
            "model_id": "giesen-wxa",
        }
        resp = await client.post("/api/machines/from-catalog", json=payload)
        assert resp.status_code == 201
        assert resp.json()["machine"]["name"] == "WxA (all sizes)"

    async def test_create_from_nonexistent_catalog(self, client: AsyncClient) -> None:
        payload = {
            "manufacturer_id": "nonexistent",
            "model_id": "nonexistent",
        }
        resp = await client.post("/api/machines/from-catalog", json=payload)
        assert resp.status_code == 404

    async def test_created_machine_is_persisted(self, client: AsyncClient) -> None:
        payload = {
            "manufacturer_id": "hottop",
            "model_id": "hottop-2k-plus",
        }
        resp = await client.post("/api/machines/from-catalog", json=payload)
        machine_id = resp.json()["id"]

        resp = await client.get(f"/api/machines/{machine_id}")
        assert resp.status_code == 200
        assert resp.json()["protocol"] == "serial"


# --- Profiles CRUD (existing tests) ---


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


# --- Machine Connection Endpoints ---


class TestMachineConnect:
    """Tests for machine connect/disconnect/status endpoints."""

    async def test_connect_nonexistent_machine(self, client: AsyncClient) -> None:
        resp = await client.post("/api/machines/nonexistent/connect")
        assert resp.status_code == 404

    async def test_disconnect_nonexistent_is_ok(self, client: AsyncClient) -> None:
        """Disconnecting a machine that isn't connected is idempotent."""
        resp = await client.post("/api/machines/nonexistent/disconnect")
        assert resp.status_code == 200
        assert resp.json()["status"] == "disconnected"

    async def test_status_not_connected(self, client: AsyncClient) -> None:
        """Status of a machine that isn't connected returns disconnected."""
        resp = await client.get("/api/machines/some-id/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["connected"] is False
        assert body["driver_state"] == "disconnected"
        assert body["session_state"] == "idle"

    async def test_connect_with_mock_manager(self, client: AsyncClient) -> None:
        """Connect succeeds when manager.connect_machine doesn't raise."""
        # Create a machine first
        payload = {
            "manufacturer_id": "carmomaq",
            "model_id": "carmomaq-stratto-2.0",
            "name": "Test Stratto",
        }
        create_resp = await client.post("/api/machines/from-catalog", json=payload)
        machine_id = create_resp.json()["id"]

        # Inject a mock manager that doesn't need real hardware
        mock_manager = MagicMock(spec=MachineManager)
        mock_manager.connect_machine = AsyncMock()
        mock_manager.disconnect_machine = AsyncMock()
        init_manager(mock_manager)

        resp = await client.post(f"/api/machines/{machine_id}/connect")
        assert resp.status_code == 200
        assert resp.json()["status"] == "connected"
        mock_manager.connect_machine.assert_called_once_with(machine_id)

    async def test_connect_driver_failure(self, client: AsyncClient) -> None:
        """Connect returns 502 when driver can't connect."""
        mock_manager = MagicMock(spec=MachineManager)
        mock_manager.connect_machine = AsyncMock(
            side_effect=ConnectionError("Cannot reach device"),
        )
        init_manager(mock_manager)

        resp = await client.post("/api/machines/some-id/connect")
        assert resp.status_code == 502
        assert "Cannot reach device" in resp.json()["detail"]

    async def test_status_connected_machine(self, client: AsyncClient) -> None:
        """Status returns connected info when machine is active."""
        from openroast.core.session import RoastSession
        from openroast.drivers.base import ConnectionState

        mock_instance = MagicMock()
        mock_driver = MagicMock()
        mock_driver.state = ConnectionState.CONNECTED
        mock_instance.driver = mock_driver
        mock_instance.session = RoastSession(machine_name="Test")

        mock_manager = MagicMock(spec=MachineManager)
        mock_manager.get_instance.return_value = mock_instance
        init_manager(mock_manager)

        resp = await client.get("/api/machines/test-id/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["connected"] is True
        assert body["driver_state"] == "connected"
        assert body["session_state"] == "idle"
