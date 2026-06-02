"""System information commands."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from . import process


def _memory_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="memory", description="Print available, used, or total memory.")
    parser.add_argument("-f", "--free", action="store_true", help="show free/available memory")
    parser.add_argument("-t", "--total", action="store_true", help="show total memory")
    parser.add_argument("-u", "--used", action="store_true", help="show used memory")
    parser.add_argument("-a", "--all", action="store_true", help="show all memory info")
    parser.add_argument("-j", "--json", action="store_true", dest="json_output", help="output JSON")
    parser.add_argument("-p", "--print", action="store_false", dest="json_output", help="output plain text")
    parser.add_argument("-v", "--value-only", action="store_true", help="output only values without labels")
    parser.add_argument("--unit", choices=["GB", "gb", "MB", "mb"], default="GB")
    parser.add_argument("--unit-label", default="G")
    parser.set_defaults(json_output=False)
    return parser


def _memory_linux() -> tuple[float, float, float]:
    completed = process.run(["free", "--giga"], capture=True)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    for line in completed.stdout.splitlines():
        if line.startswith("Mem:"):
            parts = line.split()
            return float(parts[1]), float(parts[2]), float(parts[-1])
    raise SystemExit("could not parse free output")


def _memory_macos() -> tuple[float, float, float]:
    total = int(process.output(["sysctl", "-n", "hw.memsize"]).strip()) / 1024 / 1024 / 1024
    completed = process.run(["memory_pressure"], capture=True)
    free_percent = 0.0
    for line in completed.stdout.splitlines():
        if "System-wide memory free percentage:" in line:
            free_percent = float(line.split()[-1].rstrip("%"))
            break
    available = total * free_percent / 100
    used = total - available
    return total, used, available


def _convert(value: float, unit: str) -> float:
    if unit.lower() == "gb":
        return value
    return value / 0.001


def main_memory(argv: list[str] | None = None) -> int:
    parser = _memory_parser()
    args = parser.parse_args(argv)
    show_total = args.total
    show_used = args.used
    show_free = args.free
    if args.all or not (show_total or show_used or show_free):
        show_total = show_used = show_free = True

    if os.uname().sysname == "Darwin":
        total, used, available = _memory_macos()
    elif os.uname().sysname == "Linux":
        total, used, available = _memory_linux()
    else:
        raise SystemExit(f"Unsupported operating system: {os.uname().sysname}")

    values: dict[str, float] = {}
    if show_total:
        values["total"] = _convert(total, args.unit)
    if show_used:
        values["used"] = _convert(used, args.unit)
    if show_free:
        values["available"] = _convert(available, args.unit)

    if args.json_output:
        print(json.dumps({key: f"{value:.2f}{args.unit_label}" for key, value in values.items()}))
    elif args.value_only:
        print(" ".join(f"{value:.2f}" for value in values.values()))
    else:
        labels = {"total": "Total", "used": "Used", "available": "Available"}
        for key, value in values.items():
            print(f"{labels[key]}: {value:.2f} {args.unit_label}")
    return 0


def main_download_speed(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="download_speed", description="Print approximate download speed since last run.")
    parser.add_argument("--state-file", default="/tmp/net_bytes_last")
    args = parser.parse_args(argv)

    interface = _default_interface()
    if not interface:
        print("Unable to determine default interface")
        return 1

    current = _current_rx_bytes(interface)
    if current is None:
        print(f"Unable to read byte count for interface: {interface}")
        return 1

    state_file = Path(args.state_file)
    try:
        previous = int(state_file.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        previous = current
    state_file.write_text(str(current), encoding="utf-8")

    delta = max(0, current - previous)
    if delta < 1024:
        print(f"{delta} B/s")
    elif delta < 1048576:
        print(f"{delta / 1024:.0f} KB/s")
    else:
        print(f"{delta / 1048576:.2f} MB/s")
    return 0


def _default_interface() -> str | None:
    if os.uname().sysname == "Darwin":
        completed = process.run(["route", "get", "default"], capture=True)
        for line in completed.stdout.splitlines():
            line = line.strip()
            if line.startswith("interface:"):
                return line.split(":", 1)[1].strip()
        return None

    completed = process.run(["ip", "route", "show", "default"], capture=True)
    if completed.returncode == 0:
        parts = completed.stdout.split()
        if "dev" in parts:
            return parts[parts.index("dev") + 1]
    return None


def _current_rx_bytes(interface: str) -> int | None:
    if os.uname().sysname == "Darwin":
        completed = process.run(["netstat", "-bI", interface], capture=True)
        for line in completed.stdout.splitlines():
            parts = line.split()
            if parts and parts[0] == interface and len(parts) > 6 and parts[6].isdigit():
                return int(parts[6])
        return None

    path = Path("/sys/class/net") / interface / "statistics" / "rx_bytes"
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return None

