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

    server = SimulatorServer(model, port=port, host=host)
    await server.start()

    print(f"Simulator running: {model.name}")
    print(f"  Modbus TCP: {host}:{port}")
    print(f"  Sampling interval: {model.sampling_interval_ms}ms")
    print(f"  Channels: BT={model.bt and model.bt.name}, ET={model.et and model.et.name}")
    if model.controls:
        ctrl_names = ", ".join(c.name for c in model.controls)
        print(f"  Controls: {ctrl_names}")
    print("\nPress Ctrl+C to stop.\n")

    stop_event = asyncio.Event()

    def _signal_handler() -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    await stop_event.wait()
    print("\nStopping simulator...")
    await server.stop()
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
