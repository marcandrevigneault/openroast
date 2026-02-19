"""Tests for the simulator server."""

from __future__ import annotations

import asyncio

import pytest
from pymodbus.client import AsyncModbusTcpClient

from openroast.catalog.loader import get_model
from openroast.models.catalog import (
    CatalogModel,
    ChannelConfig,
    ControlConfig,
    ModbusConnectionConfig,
    ModbusRegisterConfig,
    ProtocolType,
)
from openroast.simulator.server import SimulatorServer


def _make_test_model(port: int = 5020) -> CatalogModel:
    """Create a simple test model."""
    return CatalogModel(
        id="test-sim",
        name="Test Simulator",
        protocol=ProtocolType.MODBUS_TCP,
        sampling_interval_ms=500,
        connection=ModbusConnectionConfig(
            type="modbus_tcp",
            host="127.0.0.1",
            port=port,
            word_order_little=True,
        ),
        bt=ChannelConfig(
            name="BT",
            modbus=ModbusRegisterConfig(
                address=43, code=3, device_id=1,
                divisor=1, mode="C",
            ),
        ),
        et=ChannelConfig(
            name="ET",
            modbus=ModbusRegisterConfig(
                address=44, code=3, device_id=1,
                divisor=1, mode="C",
            ),
        ),
        extra_channels=[
            ChannelConfig(
                name="Burner",
                modbus=ModbusRegisterConfig(
                    address=45, code=3, device_id=1, divisor=0, mode="",
                ),
            ),
        ],
        controls=[
            ControlConfig(
                name="Burner", channel="burner",
                command="writeSingle(1,45,{})",
                min=0, max=100, step=1, unit="%",
            ),
        ],
    )


@pytest.fixture
def free_port() -> int:
    """Find an available TCP port."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestSimulatorServer:
    """Tests for SimulatorServer lifecycle."""

    @pytest.mark.asyncio
    async def test_start_and_stop(self, free_port: int) -> None:
        model = _make_test_model(port=free_port)
        server = SimulatorServer(model, port=free_port, seed=42)

        await server.start()
        assert server.context is not None

        await server.stop()
        assert server.context is None

    @pytest.mark.asyncio
    async def test_client_reads_initial_temperatures(self, free_port: int) -> None:
        """A Modbus client should read the initial temperatures."""
        model = _make_test_model(port=free_port)
        server = SimulatorServer(model, port=free_port, seed=42)
        await server.start()

        try:
            client = AsyncModbusTcpClient("127.0.0.1", port=free_port, timeout=2)
            await client.connect()
            assert client.connected

            # Read BT (addr 43, 1 register)
            resp = await client.read_holding_registers(43, count=1, device_id=1)
            assert not resp.isError()
            bt_raw = resp.registers[0]
            # Initial BT ≈ 25°C (±noise), divisor=1 → ~250
            assert 240 <= bt_raw <= 260

            # Read ET (addr 44)
            resp = await client.read_holding_registers(44, count=1, device_id=1)
            assert not resp.isError()
            et_raw = resp.registers[0]
            assert 240 <= et_raw <= 260

            client.close()
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_temperatures_change_after_stepping(self, free_port: int) -> None:
        """Temperatures should change after the thermal loop runs."""
        model = _make_test_model(port=free_port)
        server = SimulatorServer(model, port=free_port, seed=42)
        await server.start()

        try:
            client = AsyncModbusTcpClient("127.0.0.1", port=free_port, timeout=2)
            await client.connect()

            # Write burner to 100% via the register (addr 45)
            await client.write_register(45, 100, device_id=1)

            # Wait for thermal loop to capture and step several times
            await asyncio.sleep(3.0)

            resp = await client.read_holding_registers(44, count=1, device_id=1)
            et_raw = resp.registers[0]
            # ET should have increased from ~250 (25°C) after 3s of max burner
            assert et_raw > 255

            client.close()
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_control_write_affects_engine(self, free_port: int) -> None:
        """Writing to a control register should affect the thermal engine."""
        model = _make_test_model(port=free_port)
        server = SimulatorServer(model, port=free_port, seed=42)
        await server.start()

        try:
            client = AsyncModbusTcpClient("127.0.0.1", port=free_port, timeout=2)
            await client.connect()

            # Write burner value to register 45
            await client.write_register(45, 80, device_id=1)

            # Wait for the thermal loop to capture the control value
            await asyncio.sleep(1.0)

            # Engine should have captured the burner value
            assert server.engine.state.burner == 80.0

            client.close()
        finally:
            await server.stop()

    @pytest.mark.asyncio
    async def test_double_start_is_noop(self, free_port: int) -> None:
        model = _make_test_model(port=free_port)
        server = SimulatorServer(model, port=free_port, seed=42)
        await server.start()
        await server.start()  # Should not raise

        await server.stop()


class TestRealCatalogSimulation:
    """Integration tests using real catalog models."""

    @pytest.mark.asyncio
    async def test_stratto_simulation(self, free_port: int) -> None:
        """Full Stratto 2.0 simulation with real Modbus client."""
        model = get_model("carmomaq", "carmomaq-stratto-2.0")
        assert model is not None

        server = SimulatorServer(model, port=free_port, seed=42)
        await server.start()

        try:
            client = AsyncModbusTcpClient("127.0.0.1", port=free_port, timeout=2)
            await client.connect()

            # Read BT and ET
            bt_resp = await client.read_holding_registers(43, count=1, device_id=1)
            et_resp = await client.read_holding_registers(44, count=1, device_id=1)
            assert not bt_resp.isError()
            assert not et_resp.isError()

            # Both should be near initial values (25°C * 10 ≈ 250, ±noise)
            assert 240 <= bt_resp.registers[0] <= 260
            assert 240 <= et_resp.registers[0] <= 260

            # Read extra channels (Burner=45, Drum=46, Air=47)
            for addr in [45, 46, 47]:
                resp = await client.read_holding_registers(addr, count=1, device_id=1)
                assert not resp.isError()

            # Write burner control
            await client.write_register(45, 75, device_id=1)

            client.close()
        finally:
            await server.stop()
