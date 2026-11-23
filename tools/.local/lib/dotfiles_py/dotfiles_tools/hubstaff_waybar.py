"""Waybar module for the Hubstaff timer.

The tray icon cannot show text (Waybar's tray renders only icons and tooltips), so
this reads `HubstaffCLI status` and prints Waybar's custom-module JSON:

  hubstaff-waybar watch     run continuously: one JSON line per second while tracking
  hubstaff-waybar           print one JSON line and exit
  hubstaff-waybar toggle    stop the timer when tracking, resume it otherwise
  hubstaff-waybar open      open the Hubstaff main window

`watch` keeps the timer live without polling Hubstaff every second: it asks the CLI
for the real time every RESYNC_SECONDS (and right away on SIGUSR1, which toggle/open
send to the PIDs that watchers register under $XDG_RUNTIME_DIR/hubstaff-waybar/),
and counts seconds locally in between. While stopped it prints nothing new,
so Waybar has nothing to redraw. When Hubstaff is not running, the text is empty,
which hides the module.
"""

from __future__ import annotations

import argparse
import atexit
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from .paths import home

TIMEOUT = 5
RESYNC_SECONDS = 30


def watcher_dir() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    return Path(runtime) / "hubstaff-waybar"


def is_watcher(pid: int) -> bool:
    """True only for a live `hubstaff-waybar watch` process, so a stale PID never gets signalled."""
    try:
        args = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
    except OSError:
        return False
    return any(arg.endswith(b"hubstaff-waybar") for arg in args) and b"watch" in args


def register_watcher() -> None:
    directory = watcher_dir()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    marker = directory / str(os.getpid())
    marker.touch()
    atexit.register(marker.unlink, missing_ok=True)


def cli_path() -> Path:
    override = os.environ.get("HUBSTAFF_CLI")
    return Path(override).expanduser() if override else home() / "Hubstaff" / "HubstaffCLI.bin.x86_64"


def run_cli(*args: str) -> subprocess.CompletedProcess[str] | None:
    cli = cli_path()
    if not os.access(cli, os.X_OK):
        return None
    try:
        return subprocess.run([str(cli), *args], capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return None


def read_status() -> dict | None:
    completed = run_cli("status")
    if completed is None or completed.returncode != 0:
        return None
    for line in reversed(completed.stdout.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                data = json.loads(line)
            except ValueError:
                return None
            return data if isinstance(data, dict) else None
    return None


def parse_duration(value: str) -> int | None:
    """'2:43:14' -> 9794 seconds."""
    try:
        parts = [int(part) for part in value.split(":")]
    except ValueError:
        return None
    if len(parts) != 3 or any(part < 0 for part in parts):
        return None
    hours, minutes, seconds = parts
    return hours * 3600 + minutes * 60 + seconds


def format_duration(seconds: int) -> str:
    hours, rest = divmod(max(seconds, 0), 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}"


def render(status: dict | None, extra_seconds: int = 0) -> dict[str, str]:
    """Waybar JSON. `extra_seconds` is time counted locally since `status` was read."""
    if not status:
        return {"text": "", "tooltip": "Hubstaff is not running", "class": "offline"}
    project = status.get("active_project") or {}
    tracking = bool(status.get("tracking"))
    name = project.get("name") or "No project"
    raw = project.get("tracked_today") or "0:00:00"
    base = parse_duration(raw)
    today = format_duration(base + (extra_seconds if tracking else 0)) if base is not None else raw
    icon = "󱎫" if tracking else "󰏤"
    action = "stop" if tracking else "resume"
    return {
        "text": f"{icon} {today}",
        "tooltip": f"{'Tracking' if tracking else 'Stopped'}: {name}\nToday on this project: {today}\nLeft-click: {action} · Right-click: open Hubstaff",
        "class": "tracking" if tracking else "stopped",
    }


def emit(payload: dict[str, str]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def watch() -> int:
    resync_now = threading.Event()
    signal.signal(signal.SIGUSR1, lambda *_: resync_now.set())
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))  # run atexit cleanup
    register_watcher()
    status: dict | None = None
    synced_at = 0.0
    last_line = None
    while True:
        now = time.monotonic()
        if resync_now.is_set() or now - synced_at >= RESYNC_SECONDS:
            resync_now.clear()
            status = read_status()
            synced_at = now = time.monotonic()
        payload = render(status, int(now - synced_at))
        line = json.dumps(payload, ensure_ascii=False)
        if line != last_line:
            try:
                emit(payload)
            except BrokenPipeError:
                return 0  # Waybar went away
            last_line = line
        # Wake on the next whole second, or immediately when toggle/open signal us.
        resync_now.wait(1 - (time.monotonic() - synced_at) % 1)


def notify_watchers() -> None:
    directory = watcher_dir()
    if not directory.is_dir():
        return
    for marker in directory.iterdir():
        pid = int(marker.name) if marker.name.isdigit() else None
        if pid is not None and is_watcher(pid):
            try:
                os.kill(pid, signal.SIGUSR1)
            except ProcessLookupError:
                marker.unlink(missing_ok=True)
        else:
            marker.unlink(missing_ok=True)  # stale marker


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hubstaff-waybar", description="Show and control the Hubstaff timer in Waybar.")
    parser.add_argument("action", nargs="?", choices=("status", "watch", "toggle", "open"), default="status")
    args = parser.parse_args(argv)

    if args.action == "status":
        emit(render(read_status()))
        return 0
    if args.action == "watch":
        return watch()
    if args.action == "toggle":
        status = read_status()
        if status is None:
            return 1
        run_cli("stop" if status.get("tracking") else "resume")
    else:
        run_cli("send", "open-main-window")
    notify_watchers()
    return 0
