#!/usr/bin/env python3
"""Modbus TCP register prober — monitors register changes in real time.

Connect to a Modbus TCP device and continuously read holding registers,
highlighting any value that changes between polls.  Useful for reverse-
engineering which registers correspond to physical controls.

Usage examples:

    # Probe Stratto 2.0 defaults (regs 40-65, device 1)
    python tools/modbus_prober.py

    # Custom range
    python tools/modbus_prober.py --host 192.168.5.11 --start 0 --count 100

    # Faster polling
    python tools/modbus_prober.py --interval 0.5

    # Snapshot mode — read once and exit
    python tools/modbus_prober.py --once
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime

from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException


# ANSI colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Modbus TCP register prober — monitors register changes.",
    )
    p.add_argument("--host", default="192.168.5.11", help="Modbus TCP host (default: 192.168.5.11)")
    p.add_argument("--port", type=int, default=502, help="Modbus TCP port (default: 502)")
    p.add_argument("--device-id", type=int, default=1, help="Modbus device/unit ID (default: 1)")
    p.add_argument("--start", type=int, default=40, help="First register address (default: 40)")
    p.add_argument("--count", type=int, default=30, help="Number of registers to read (default: 30)")
    p.add_argument("--interval", type=float, default=1.0, help="Poll interval in seconds (default: 1.0)")
    p.add_argument("--once", action="store_true", help="Read once and exit")
    p.add_argument("--code", type=int, default=3, choices=[3, 4],
                   help="Function code: 3=holding, 4=input (default: 3)")
    p.add_argument("--log", action="store_true", help="Log all changes to modbus_probe.log")
    return p.parse_args()


def _read_call(
    client: ModbusTcpClient,
    start: int,
    count: int,
    device_id: int,
    code: int,
) -> object:
    """Try multiple kwarg conventions across pymodbus versions."""
    fn = client.read_input_registers if code == 4 else client.read_holding_registers
    # pymodbus 3.7+: device_id=  ;  pymodbus <3.7: slave=  ;  some: unit=
    for kw in ("slave", "device_id", "unit"):
        try:
            return fn(start, count=count, **{kw: device_id})
        except TypeError:
            continue
    # Last resort — positional only
    return fn(start, count)


def read_registers(
    client: ModbusTcpClient,
    start: int,
    count: int,
    device_id: int,
    code: int,
) -> list[int] | None:
    """Read a block of registers. Returns list of values or None on error."""
    try:
        resp = _read_call(client, start, count, device_id, code)
        if resp.isError():
            return None
        return resp.registers
    except (ModbusException, AttributeError):
        return None


def print_header(args: argparse.Namespace) -> None:
    print(f"\n{BOLD}Modbus TCP Prober{RESET}")
    print(f"  Host:      {args.host}:{args.port}")
    print(f"  Device ID: {args.device_id}")
    print(f"  Registers: {args.start} - {args.start + args.count - 1} "
          f"(FC{args.code}: {'holding' if args.code == 3 else 'input'})")
    print(f"  Interval:  {args.interval}s")
    print(f"  {DIM}Press Ctrl+C to stop{RESET}\n")


def format_table(
    start: int,
    values: list[int],
    prev: list[int] | None,
    changed_ever: set[int],
) -> str:
    """Format register values as a table, highlighting changes."""
    lines = []
    lines.append(f"  {DIM}{'Reg':>5}  {'Dec':>6}  {'Hex':>6}  {'Bin':>18}{RESET}")
    lines.append(f"  {DIM}{'─' * 5}  {'─' * 6}  {'─' * 6}  {'─' * 18}{RESET}")

    for i, val in enumerate(values):
        addr = start + i
        just_changed = prev is not None and prev[i] != val
        ever_changed = addr in changed_ever

        if just_changed:
            color = RED + BOLD
            marker = " ◄"
        elif ever_changed:
            color = YELLOW
            marker = ""
        else:
            color = DIM
            marker = ""

        lines.append(
            f"  {color}{addr:>5}  {val:>6}  0x{val:04X}  {val:016b}{RESET}"
            f"{RED}{marker}{RESET}"
        )

    return "\n".join(lines)


def main() -> None:
    args = parse_args()

    log_file = None
    if args.log:
        log_file = open("modbus_probe.log", "a")  # noqa: SIM115
        log_file.write(f"\n--- Probe session {datetime.now().isoformat()} ---\n")
        log_file.write(f"Host: {args.host}:{args.port}  Device: {args.device_id}  "
                       f"Regs: {args.start}-{args.start + args.count - 1}\n")

    print_header(args)

    client = ModbusTcpClient(args.host, port=args.port, timeout=3)
    if not client.connect():
        print(f"{RED}Failed to connect to {args.host}:{args.port}{RESET}")
        sys.exit(1)

    print(f"{GREEN}Connected.{RESET}\n")

    prev_values: list[int] | None = None
    changed_ever: set[int] = set()
    poll_count = 0

    try:
        while True:
            values = read_registers(client, args.start, args.count, args.device_id, args.code)
            poll_count += 1

            if values is None:
                print(f"{RED}Read error (poll #{poll_count}){RESET}")
                time.sleep(args.interval)
                continue

            # Track which registers changed
            if prev_values is not None:
                for i, (old, new) in enumerate(zip(prev_values, values)):
                    if old != new:
                        addr = args.start + i
                        changed_ever.add(addr)
                        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        change_msg = (
                            f"  {CYAN}[{ts}]{RESET} "
                            f"Reg {RED}{BOLD}{addr}{RESET}: "
                            f"{old} → {GREEN}{BOLD}{new}{RESET}"
                        )
                        print(change_msg)
                        if log_file:
                            log_file.write(f"[{ts}] reg {addr}: {old} -> {new}\n")
                            log_file.flush()

            # Clear screen and print table (only on first read or if --once)
            if poll_count == 1 or args.once:
                print(format_table(args.start, values, prev_values, changed_ever))

            if args.once:
                break

            prev_values = values
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print(f"\n\n{BOLD}Summary — registers that changed:{RESET}")
        if changed_ever:
            for addr in sorted(changed_ever):
                print(f"  Reg {YELLOW}{addr}{RESET}")
        else:
            print(f"  {DIM}(none){RESET}")
        print()
        if log_file:
            log_file.write(f"Changed registers: {sorted(changed_ever)}\n")
    finally:
        client.close()
        if log_file:
            log_file.close()


if __name__ == "__main__":
    main()
