"""Reconnect trusted Bluetooth audio devices from the PC side.

Earbuds choose where to connect when they leave the case, and BlueZ only retries
after a connection drops, so a trusted headset that came up while the PC was not
ready simply stays disconnected. This asks BlueZ to connect each trusted audio
device (one with the Audio Sink profile) that is paired but not connected.

After a device disconnects (a manual disconnect, or earbuds back in the case) it
waits COOLDOWN seconds before trying again, so a deliberate disconnect is not
undone immediately; earbuds taken out within that time reconnect on their own,
because the PC was their last device.

  bt-autoconnect                 run continuously (started by hypr-startup)
  bt-autoconnect --once          one pass, then exit
  bt-autoconnect --once --dry-run  show what it would do
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field

from .process import require

INTERVAL = 30.0
COOLDOWN = 600.0
CONNECT_TIMEOUT = 25
AUDIO_SINK = "0000110b-0000-1000-8000-00805f9b34fb"
MAC = re.compile(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}")


@dataclass
class DeviceInfo:
    mac: str
    available: bool
    paired: bool = False
    trusted: bool = False
    connected: bool = False
    audio: bool = False


@dataclass
class Memory:
    """What the loop remembers about one device between passes."""
    was_connected: bool = False
    quiet_until: float = 0.0


@dataclass
class Tracker:
    devices: dict[str, Memory] = field(default_factory=dict)


def parse_info(mac: str, text: str) -> DeviceInfo:
    if "not available" in text or not text.strip():
        return DeviceInfo(mac, available=False)

    def flag(name: str) -> bool:
        match = re.search(rf"^\s*{name}:\s*(yes|no)\s*$", text, re.M)
        return bool(match and match.group(1) == "yes")

    return DeviceInfo(mac, True, flag("Paired"), flag("Trusted"), flag("Connected"), AUDIO_SINK in text)


def parse_devices(text: str) -> list[str]:
    return [m.group(0) for line in text.splitlines() if line.startswith("Device ") and (m := MAC.search(line))]


def decide(info: DeviceInfo, memory: Memory, now: float) -> str:
    """'connect' or 'wait'. Updates `memory` (connection seen, cooldown after a disconnect)."""
    if not (info.available and info.paired and info.trusted and info.audio):
        return "wait"
    if info.connected:
        memory.was_connected = True
        return "wait"
    if memory.was_connected:
        memory.was_connected = False
        memory.quiet_until = now + COOLDOWN
        return "wait"
    return "connect" if now >= memory.quiet_until else "wait"


def _ctl(*args: str, timeout: float = 5) -> str:
    try:
        return subprocess.run(["bluetoothctl", *args], capture_output=True, text=True, timeout=timeout).stdout
    except subprocess.TimeoutExpired:
        return ""


def adapter_powered() -> bool:
    return bool(re.search(r"^\s*Powered:\s*yes", _ctl("show"), re.M))


def run_pass(tracker: Tracker, *, macs: list[str] | None, dry_run: bool, now: float | None = None) -> list[str]:
    """One check of every candidate device. Returns log lines for anything that happened."""
    now = time.monotonic() if now is None else now
    if not adapter_powered():
        return []
    log = []
    for mac in macs or parse_devices(_ctl("devices", "Trusted")):
        memory = tracker.devices.setdefault(mac, Memory())
        before = memory.was_connected
        info = parse_info(mac, _ctl("info", mac))
        action = decide(info, memory, now)
        if before and not memory.was_connected:
            log.append(f"{mac} disconnected; not reconnecting for {COOLDOWN / 60:.0f} min")
        if action == "connect":
            if dry_run:
                log.append(f"+ bluetoothctl connect {mac}")
                continue
            result = _ctl("connect", mac, timeout=CONNECT_TIMEOUT)
            if "Connection successful" in result:
                memory.was_connected = True
                log.append(f"{mac} connected")
    return log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bt-autoconnect", description="Reconnect trusted Bluetooth audio devices from the PC side.")
    parser.add_argument("--device", action="append", default=[], help="only this MAC (repeatable; default: every trusted audio device)")
    parser.add_argument("--once", action="store_true", help="one pass, then exit")
    parser.add_argument("--dry-run", action="store_true", help="show connect attempts instead of making them")
    args = parser.parse_args(argv)
    require("bluetoothctl")
    macs = [mac.upper() for mac in args.device] or None
    tracker = Tracker()
    while True:
        for line in run_pass(tracker, macs=macs, dry_run=args.dry_run):
            print(f"bt-autoconnect: {line}", file=sys.stderr, flush=True)
        if args.once:
            return 0
        time.sleep(INTERVAL)
