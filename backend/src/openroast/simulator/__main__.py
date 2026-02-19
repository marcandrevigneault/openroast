"""CLI entry point for the roaster machine simulator.

Usage:
    python -m openroast.simulator --manufacturer carmomaq --model carmomaq-stratto-2.0
    python -m openroast.simulator --manufacturer carmomaq --model carmomaq-stratto-2.0 --port 5020
    python -m openroast.simulator --list
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys


def _list_models() -> None:
    """Print all simulatable (Modbus) models from the catalog."""
    from openroast.catalog.loader import get_manufacturers
    from openroast.models.catalog import ProtocolType

    manufacturers = get_manufacturers()
    modbus_types = {ProtocolType.MODBUS_TCP, ProtocolType.MODBUS_RTU}

    print("Available Modbus machines for simulation:\n")
    for mfr in manufacturers:
        modbus_models = [m for m in mfr.models if m.protocol in modbus_types]
        if not modbus_models:
            continue
        print(f"  {mfr.name} ({mfr.id}):")
        for model in modbus_models:
            print(f"    --manufacturer {mfr.id} --model {model.id}")
            print(f"      {model.name} ({model.protocol})")
        print()


def _provision_machine(
    manufacturer_id: str,
    model_id: str,
    host: str,
    port: int,
) -> str:
    """Create a SavedMachine JSON file pointing to the simulator.

    Writes directly to the backend data directory so the machine
    appears in the UI when the backend loads saved machines.

    Returns:
        The machine ID.
    """
    from pathlib import Path

    from openroast.catalog.loader import get_model
    from openroast.core.machine_storage import MachineStorage
    from openroast.models.catalog import ModbusConnectionConfig
    from openroast.models.machine import SavedMachine

    model = get_model(manufacturer_id, model_id)
    if model is None:
        print(f"Error: Model '{model_id}' not found")
        sys.exit(1)

    # Override connection to point to simulator
    conn = model.connection
    if isinstance(conn, ModbusConnectionConfig):
        conn = ModbusConnectionConfig(
            type="modbus_tcp",
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
        catalog_model_id=model_id,
        protocol=model.protocol,
        connection=conn,
        sampling_interval_ms=model.sampling_interval_ms,
        et=model.et,
        bt=model.bt,
        extra_channels=model.extra_channels,
        controls=model.controls,
    )

    # Write to the standard data directory
    data_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "machines"
    storage = MachineStorage(data_dir)
    storage.save(machine)

    return machine.id


def _cleanup_machine(machine_id: str) -> None:
    """Remove the provisioned SavedMachine JSON file."""
    from pathlib import Path

    data_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "machines"
    machine_file = data_dir / f"{machine_id}.json"
    if machine_file.exists():
        machine_file.unlink()


async def _run_simulator(
    manufacturer_id: str,
    model_id: str,
    port: int,
    host: str,
) -> None:
    """Run a simulator until interrupted."""
    from openroast.catalog.loader import get_model
    from openroast.simulator.server import SimulatorServer

    model = get_model(manufacturer_id, model_id)
    if model is None:
        print(f"Error: Model '{model_id}' not found for manufacturer '{manufacturer_id}'")
        print("Use --list to see available models.")
        sys.exit(1)

    # Provision a SavedMachine so the UI can see it
    machine_id = _provision_machine(manufacturer_id, model_id, host, port)

    server = SimulatorServer(model, port=port, host=host)
    await server.start()

    print(f"Simulator running: {model.name}")
    print(f"  Modbus TCP: {host}:{port}")
    print(f"  Machine ID: {machine_id}")
    print(f"  Sampling interval: {model.sampling_interval_ms}ms")
    print(f"  Channels: BT={model.bt and model.bt.name}, ET={model.et and model.et.name}")
    if model.controls:
        ctrl_names = ", ".join(c.name for c in model.controls)
        print(f"  Controls: {ctrl_names}")
    print("\nThe machine is now available in the UI. Reload the page to see it.")
    print("Press Ctrl+C to stop.\n")

    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    await stop_event.wait()
    print("\nStopping simulator...")
    await server.stop()
    _cleanup_machine(machine_id)
    print("Done.")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="python -m openroast.simulator",
        description="Roaster machine simulator — Modbus TCP server from catalog",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="List all simulatable machines from the catalog",
    )
    parser.add_argument(
        "--manufacturer", type=str, default="",
        help="Manufacturer ID (e.g. 'carmomaq')",
    )
    parser.add_argument(
        "--model", type=str, default="",
        help="Model ID (e.g. 'carmomaq-stratto-2.0')",
    )
    parser.add_argument(
        "--port", type=int, default=5020,
        help="TCP port to listen on (default: 5020)",
    )
    parser.add_argument(
        "--host", type=str, default="127.0.0.1",
        help="TCP host to bind to (default: 127.0.0.1)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    if args.list:
        _list_models()
        return

    if not args.manufacturer or not args.model:
        parser.error("--manufacturer and --model are required (or use --list)")

    asyncio.run(_run_simulator(args.manufacturer, args.model, args.port, args.host))


if __name__ == "__main__":
    main()
