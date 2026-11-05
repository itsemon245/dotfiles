"""Deliver queued notifications from unattended services to the desktop."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import stat
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from . import notify, process
from .cli import ToolError, add_dry_run

HISTORY_DAYS = 30
NORMAL_TIMEOUT_MS = 10000
BUS_NOTIFIERS = ("dunstify", "notify-send")
OWNER_CHECK = [
    "busctl",
    "--user",
    "call",
    "org.freedesktop.DBus",
    "/org/freedesktop/DBus",
    "org.freedesktop.DBus",
    "NameHasOwner",
    "s",
    "org.freedesktop.Notifications",
]


def notifier_ready() -> bool:
    """Check for a running notifier without activating one.

    Sending to a missing notifier would make D-Bus start dunst, even with no
    display to show anything on.
    """
    if process.command_exists("busctl"):
        result = process.run(OWNER_CHECK, capture=True)
        if result.returncode == 0 and result.stdout.strip() == "b true":
            return True
    if any(process.command_exists(tool) for tool in BUS_NOTIFIERS):
        return False
    return process.command_exists("hyprctl")


def wait_for_notifier(seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while True:
        if notifier_ready():
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.5)


def pending() -> list[Path]:
    return sorted(notify.queue_dir("inbox").glob("*.json"))


def load(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Return the message, or the reason it must be set aside."""
    info = os.lstat(path)
    if not stat.S_ISREG(info.st_mode):
        return None, "not a regular file"
    if info.st_size > notify.MAX_MESSAGE_BYTES:
        return None, "too large"
    try:
        message = json.loads(path.read_bytes().decode())
    except ValueError:
        return None, "not valid JSON"
    error = notify.message_error(message)
    return (None, error) if error else (message, None)


def reject(path: Path, reason: str) -> None:
    print(f"notify-relay: rejected {path.name}: {reason}", file=sys.stderr)
    os.replace(path, notify.queue_dir("rejected") / path.name)


def record(message: dict[str, Any], status: str) -> None:
    entry = {
        **message,
        "status": status,
        "handled_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n"
    try:
        with (notify.queue_dir("sent") / f"{message['service']}.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(line)
    except OSError as error:
        print(f"notify-relay: could not record history: {error}", file=sys.stderr)


def is_expired(message: dict[str, Any], now: datetime) -> bool:
    expires = message.get("expires")
    return expires is not None and datetime.fromisoformat(expires) <= now


def deliver(message: dict[str, Any]) -> bool:
    urgency = message.get("urgency", "normal")
    return notify.notify(
        message["title"],
        message.get("body", ""),
        urgency=urgency,
        icon=message.get("icon"),
        timeout=0 if urgency == "critical" else NORMAL_TIMEOUT_MS,
        tag=message.get("key"),
        escape=True,
    )


def drain() -> bool:
    """Deliver until the inbox is empty. Return False if a delivery failed.

    It rescans because a path unit cannot see files that land while this runs.
    """
    notify.prepare_queue("inbox", "sent", "rejected")
    while True:
        messages: list[tuple[Path, dict[str, Any]]] = []
        for path in pending():
            message, reason = load(path)
            if message is None:
                reject(path, reason or "unknown")
            else:
                messages.append((path, message))
        if not messages:
            return True

        newest = {message["key"]: path for path, message in messages if "key" in message}
        now = datetime.now().astimezone()
        for path, message in messages:
            if is_expired(message, now):
                status = "expired"
            elif "key" in message and newest[message["key"]] != path:
                status = "replaced"
            elif deliver(message):
                status = "delivered"
            else:
                return False
            record(message, status)
            path.unlink()


def _is_old(line: str, cutoff: datetime) -> bool:
    try:
        return datetime.fromisoformat(json.loads(line)["handled_at"]) < cutoff
    except (KeyError, TypeError, ValueError):
        return False


def prune(now: datetime) -> None:
    """Drop history and rejected files past the retention period."""
    cutoff = now - timedelta(days=HISTORY_DAYS)
    for path in notify.queue_dir("sent").glob("*.jsonl"):
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        kept = [line for line in lines if not _is_old(line, cutoff)]
        if len(kept) != len(lines):
            descriptor, temp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.writelines(kept)
            os.replace(temp, path)
    for path in notify.queue_dir("rejected").glob("*"):
        if os.lstat(path).st_mtime < cutoff.timestamp():
            path.unlink()


def relay(wait: float) -> int:
    notify.prepare_queue("inbox", "sent", "rejected")
    with (notify.queue_root() / "lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if pending() and wait_for_notifier(wait):
            drain()
        prune(datetime.now().astimezone())
    return 0


def preview() -> int:
    for path in pending():
        message, reason = load(path)
        if message is None:
            print(f"would reject {path.name}: {reason}")
        else:
            print(f"would deliver [{message['service']}] {message['title']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deliver queued notifications to the desktop.")
    parser.add_argument("--wait", type=float, default=0, metavar="SECONDS", help="wait this long for a notifier to appear")
    add_dry_run(parser)
    args = parser.parse_args(argv)
    if args.dry_run:
        return preview()
    try:
        return relay(args.wait)
    except OSError as error:
        raise ToolError(f"could not process the notification queue: {error}") from error


def post_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Queue a notification from an unattended service.")
    parser.add_argument("--service", required=True, help="sender name, using a-z, 0-9 and dashes")
    parser.add_argument("--title", required=True)
    parser.add_argument("--body", default="")
    parser.add_argument("--icon", help="freedesktop icon name")
    parser.add_argument("--urgency", choices=notify.URGENCIES, default="normal")
    parser.add_argument("--key", help="a newer message with the same key replaces this one")
    parser.add_argument("--ttl", type=int, metavar="SECONDS", help="drop the message if undelivered after this long")
    args = parser.parse_args(argv)
    queued = notify.post(
        args.service,
        args.title,
        args.body,
        icon=args.icon,
        urgency=args.urgency,
        key=args.key,
        ttl=args.ttl,
    )
    return 0 if queued else 1
