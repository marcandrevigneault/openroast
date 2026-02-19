"""Roaster machine simulator.

Provides a Modbus TCP server that simulates any machine from the catalog,
enabling full-stack testing without real hardware.
"""

from openroast.simulator.engine import ThermalEngine, ThermalState
from openroast.simulator.manager import SimulatorManager
from openroast.simulator.register_map import build_server_context, encode_value, write_channel
from openroast.simulator.server import SimulatorServer

__all__ = [
    "SimulatorManager",
    "SimulatorServer",
    "ThermalEngine",
    "ThermalState",
    "build_server_context",
    "encode_value",
    "write_channel",
]
