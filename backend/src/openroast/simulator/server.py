"""Modbus TCP simulator server.

Combines the register map builder, thermal engine, and pymodbus TCP
server into a single runnable unit that simulates a roasting machine.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING

from pymodbus.server import ModbusTcpServer

from openroast.simulator.engine import ThermalEngine
from openroast.simulator.register_map import (
    build_server_context,
    read_register_raw,
    write_channel,
)

if TYPE_CHECKING:
    from pymodbus.datastore import ModbusServerContext

    from openroast.models.catalog import CatalogModel

logger = logging.getLogger(__name__)


class SimulatorServer:
    """A Modbus TCP server that simulates a roasting machine.

    Loads a catalog machine definition, builds the register map,
    and runs a thermal simulation that updates register values
    at the machine's sampling interval.

    Args:
        model: Catalog machine definition.
        port: TCP port to listen on.
        host: TCP host to bind to.
        seed: Optional RNG seed for deterministic thermal simulation.
    """

    def __init__(
        self,
        model: CatalogModel,
        port: int = 5020,
        host: str = "127.0.0.1",
        seed: int | None = None,
    ) -> None:
        self.model = model
        self.port = port
        self.host = host
        self.engine = ThermalEngine(seed=seed)
        self._context: ModbusServerContext | None = None
        self._server: ModbusTcpServer | None = None
        self._update_task: asyncio.Task[None] | None = None
        self._running = False

    @property
    def context(self) -> ModbusServerContext | None:
        """The active Modbus server context (register datastore)."""
        return self._context

    async def start(self) -> None:
        """Start the simulator server and thermal update loop."""
        if self._running:
            return

        self._context = build_server_context(self.model)
        self._server = ModbusTcpServer(
            context=self._context,
            address=(self.host, self.port),
        )
        await self._server.listen()
        self._running = True

        self._update_task = asyncio.create_task(
            self._thermal_loop(),
            name=f"sim-thermal-{self.model.id}",
        )
        logger.info(
            "Simulator started: %s on %s:%d",
            self.model.name, self.host, self.port,
        )

    async def stop(self) -> None:
        """Stop the simulator server and thermal loop."""
        self._running = False

        if self._update_task:
            self._update_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._update_task
            self._update_task = None

        if self._server:
            await self._server.shutdown()
            self._server = None

        self._context = None
        logger.info("Simulator stopped: %s", self.model.name)

    async def _thermal_loop(self) -> None:
        """Periodically step the thermal engine and update registers."""
        from openroast.models.catalog import ModbusConnectionConfig

        conn = self.model.connection
        word_order_little = True
        if isinstance(conn, ModbusConnectionConfig):
            word_order_little = conn.word_order_little

        # Build control address map for reading driver writes
        control_addrs = self._build_control_map()

        interval_s = self.model.sampling_interval_ms / 1000.0

        while self._running:
            try:
                # Read control register values written by the driver
                self._capture_controls(control_addrs)

                # Step thermal engine
                state = self.engine.step(dt=interval_s)

                # Write updated temperatures to registers
                assert self._context is not None
                if self.model.bt and self.model.bt.modbus:
                    write_channel(
                        self._context, self.model.bt.modbus,
                        state.bt, word_order_little,
                    )
                if self.model.et and self.model.et.modbus:
                    write_channel(
                        self._context, self.model.et.modbus,
                        state.et, word_order_little,
                    )

                # Write extra channel values (burner/air/drum echo)
                self._update_extra_channels(state, word_order_little)

            except Exception:
                logger.exception("Thermal loop error")

            await asyncio.sleep(interval_s)

    def _build_control_map(self) -> dict[str, tuple[int, int]]:
        """Build channel → (device_id, address) map for controls."""
        from openroast.simulator.register_map import _parse_control_address

        result: dict[str, tuple[int, int]] = {}
        for ctrl in self.model.controls:
            parsed = _parse_control_address(ctrl)
            if parsed:
                result[ctrl.channel] = parsed
        return result

    def _capture_controls(
        self, control_addrs: dict[str, tuple[int, int]],
    ) -> None:
        """Read control registers and feed values to thermal engine."""
        if not self._context:
            return

        for channel, (device_id, address) in control_addrs.items():
            try:
                raw = read_register_raw(self._context, device_id, address)
                self.engine.set_control(channel, float(raw))
            except Exception:
                pass

    def _update_extra_channels(
        self, state: ThermalEngine | None = None, word_order_little: bool = True,
    ) -> None:
        """Write extra channel values based on thermal state."""
        if not self._context:
            return

        ts = self.engine.state

        # Map extra channel names to thermal state values
        channel_values: dict[str, float] = {
            "burner": ts.burner,
            "gas": ts.burner,
            "gas1": ts.burner,
            "gas2": ts.burner,
            "heater": ts.burner,
            "power": ts.burner,
            "air": ts.airflow,
            "airflow": ts.airflow,
            "fan": ts.airflow,
            "cooling": ts.airflow,
            "drum": ts.drum,
        }

        for ch in self.model.extra_channels:
            if ch.modbus:
                val = channel_values.get(ch.name.lower(), 0.0)
                write_channel(
                    self._context, ch.modbus, val, word_order_little,
                )
