"""Simulator lifecycle manager.

Manages multiple running simulator instances, each serving a Modbus TCP
server for a specific catalog machine. Can allocate free ports, create
SavedMachine entries for connection, and start/stop simulators.
"""

from __future__ import annotations

import logging
import socket
from dataclasses import dataclass
from typing import TYPE_CHECKING

from openroast.simulator.server import SimulatorServer

if TYPE_CHECKING:
    from openroast.core.machine_storage import MachineStorage
    from openroast.models.catalog import CatalogModel

logger = logging.getLogger(__name__)


@dataclass
class SimulatorInfo:
    """Information about a running simulator."""

    machine_id: str
    catalog_id: str
    manufacturer_id: str
    name: str
    port: int
    host: str


def _find_free_port() -> int:
    """Find an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class SimulatorManager:
    """Manages running simulator instances.

    Args:
        machine_storage: Storage backend for creating SavedMachine entries.
    """

    def __init__(self, machine_storage: MachineStorage | None = None) -> None:
        self._machine_storage = machine_storage
        self._instances: dict[str, SimulatorServer] = {}
        self._info: dict[str, SimulatorInfo] = {}

    async def start(
        self,
        model: CatalogModel,
        manufacturer_id: str,
        port: int = 0,
        host: str = "127.0.0.1",
    ) -> SimulatorInfo:
        """Start a simulator for a catalog machine.

        Args:
            model: Catalog machine definition.
            manufacturer_id: Manufacturer ID for storage reference.
            port: TCP port (0 = auto-assign).
            host: TCP host to bind to.

        Returns:
            SimulatorInfo with machine_id and connection details.

        Raises:
            ValueError: If a simulator for this catalog model is already running.
        """
        # Check for duplicate
        for info in self._info.values():
            if info.catalog_id == model.id:
                msg = f"Simulator already running for {model.id} on port {info.port}"
                raise ValueError(msg)

        if port == 0:
            port = _find_free_port()

        server = SimulatorServer(model, port=port, host=host)
        await server.start()

        # Create a SavedMachine pointing to the simulator
        machine_id = self._create_saved_machine(model, manufacturer_id, host, port)

        info = SimulatorInfo(
            machine_id=machine_id,
            catalog_id=model.id,
            manufacturer_id=manufacturer_id,
            name=f"{model.name} (Simulator)",
            port=port,
            host=host,
        )

        self._instances[machine_id] = server
        self._info[machine_id] = info

        logger.info("Started simulator %s on %s:%d (machine_id=%s)",
                     model.name, host, port, machine_id)
        return info

    async def stop(self, machine_id: str) -> None:
        """Stop a running simulator.

        Args:
            machine_id: The machine ID returned by start().

        Raises:
            KeyError: If no simulator is running for this machine_id.
        """
        server = self._instances.pop(machine_id, None)
        if server is None:
            msg = f"No simulator running for machine_id={machine_id}"
            raise KeyError(msg)

        await server.stop()
        self._info.pop(machine_id, None)

        # Clean up the saved machine
        if self._machine_storage:
            self._machine_storage.delete(machine_id)

        logger.info("Stopped simulator for machine_id=%s", machine_id)

    def list_running(self) -> list[SimulatorInfo]:
        """List all running simulators."""
        return list(self._info.values())

    def get(self, machine_id: str) -> SimulatorInfo | None:
        """Get info for a running simulator."""
        return self._info.get(machine_id)

    async def stop_all(self) -> None:
        """Stop all running simulators."""
        for machine_id in list(self._instances):
            try:
                await self.stop(machine_id)
            except Exception:
                logger.exception("Error stopping simulator %s", machine_id)

    def _create_saved_machine(
        self,
        model: CatalogModel,
        manufacturer_id: str,
        host: str,
        port: int,
    ) -> str:
        """Create a SavedMachine pointing to the simulator."""
        from openroast.models.catalog import ModbusConnectionConfig
        from openroast.models.machine import SavedMachine

        # Override connection to point to simulator
        conn = model.connection
        if isinstance(conn, ModbusConnectionConfig):
            conn = ModbusConnectionConfig(
                type=conn.type,
                host=host,
                port=port,
                baudrate=conn.baudrate,
                bytesize=conn.bytesize,
                parity=conn.parity,
                stopbits=conn.stopbits,
                timeout=conn.timeout,
                word_order_little=conn.word_order_little,
            )

        machine = SavedMachine(
            name=f"{model.name} (Simulator)",
            catalog_manufacturer_id=manufacturer_id,
            catalog_model_id=model.id,
            protocol=model.protocol,
            connection=conn,
            sampling_interval_ms=model.sampling_interval_ms,
            et=model.et,
            bt=model.bt,
            extra_channels=model.extra_channels,
            controls=model.controls,
        )

        if self._machine_storage:
            self._machine_storage.save(machine)

        return machine.id
