"""Desktop notifications, and a file queue for services without a session.

Interactive tools call notify(). Unattended services call post(), which only
writes a file; notify-relay delivers it when a notifier is available.
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from . import process
from .paths import xdg_state_home

MAX_TITLE = 256
MAX_BODY = 4096
MAX_MESSAGE_BYTES = 16 * 1024
URGENCIES = ("low", "normal", "critical")
SERVICE_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
KEY_PATTERN = re.compile(r"[A-Za-z0-9._:-]{1,128}")
ICON_PATTERN = re.compile(r"[\w./+][\w./+-]{0,255}")


def _bus_args(
    tool: str,
    title: str,
    message: str,
    *,
    urgency: str,
    icon: str | None,
    timeout: int,
    replace_id: int | None,
    tag: str | None,
) -> list[str]:
    args = [tool, "-u", urgency, "-t", str(timeout)]
    if replace_id is not None and tool == "dunstify":
        args.extend(["-r", str(replace_id)])
    if icon:
        args.extend(["-i", icon])
    if tag:
        args.extend(["-h", f"string:x-dunst-stack-tag:{tag}"])
    return [*args, "--", title, message]


def notify(
    title: str,
    message: str = "",
    *,
    urgency: str = "normal",
    icon: str | None = None,
    timeout: int = 5000,
    replace_id: int | None = None,
    tag: str | None = None,
    escape: bool = False,
    dry_run: bool = False,
) -> bool:
    """Show a notification, and return whether a notifier accepted it."""
    for tool in ("dunstify", "notify-send"):
        if process.command_exists(tool):
            text = (html.escape(title, quote=False), html.escape(message, quote=False)) if escape else (title, message)
            args = _bus_args(
                tool,
                *text,
                urgency=urgency,
                icon=icon,
                timeout=timeout,
                replace_id=replace_id,
                tag=tag,
            )
            return process.run(args, dry_run=dry_run, quiet=True).returncode == 0

    if process.command_exists("hyprctl"):
        return (
            process.run(
                ["hyprctl", "notify", "-1", str(timeout), "rgb(ffb86c)", f"{title}: {message}"],
                dry_run=dry_run,
                quiet=True,
            ).returncode
            == 0
        )

    if urgency == "critical":
        print(f"{title}: {message}")
    return False


def queue_root() -> Path:
    return xdg_state_home() / "notify"


def queue_dir(name: str) -> Path:
    return queue_root() / name


def prepare_queue(*names: str) -> None:
    for path in (queue_root(), *map(queue_dir, names)):
        path.mkdir(mode=0o700, parents=True, exist_ok=True)


def message_error(message: Any) -> str | None:
    """Return why a queued message is invalid, or None when it is valid."""
    if not isinstance(message, dict):
        return "message is not an object"
    service = message.get("service")
    if not isinstance(service, str) or not SERVICE_PATTERN.fullmatch(service):
        return "invalid service name"
    title = message.get("title")
    if not isinstance(title, str) or not title.strip() or len(title) > MAX_TITLE:
        return "invalid title"
    body = message.get("body", "")
    if not isinstance(body, str) or len(body) > MAX_BODY:
        return "invalid body"
    if message.get("urgency", "normal") not in URGENCIES:
        return "invalid urgency"
    icon = message.get("icon")
    if icon is not None and not (isinstance(icon, str) and ICON_PATTERN.fullmatch(icon)):
        return "invalid icon"
    key = message.get("key")
    if key is not None and not (isinstance(key, str) and KEY_PATTERN.fullmatch(key)):
        return "invalid key"
    expires = message.get("expires")
    if expires is not None:
        try:
            if datetime.fromisoformat(expires).tzinfo is None:
                return "expiry has no timezone"
        except (TypeError, ValueError):
            return "invalid expiry"
    return None


def post(
    service: str,
    title: str,
    body: str = "",
    *,
    icon: str | None = None,
    urgency: str = "normal",
    key: str | None = None,
    ttl: int | None = None,
) -> bool:
    """Queue a notification. Never raises, so it cannot break the caller."""
    message: dict[str, str] = {"service": service, "title": title}
    if body:
        message["body"] = body
    if icon:
        message["icon"] = icon
    if urgency != "normal":
        message["urgency"] = urgency
    if key:
        message["key"] = key
    if ttl is not None:
        expires = datetime.now().astimezone() + timedelta(seconds=ttl)
        message["expires"] = expires.isoformat(timespec="seconds")

    error = message_error(message)
    if error:
        print(f"notify: {error}", file=sys.stderr)
        return False

    data = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode()
    if len(data) > MAX_MESSAGE_BYTES:
        print("notify: message is too large", file=sys.stderr)
        return False

    temp_path = None
    try:
        prepare_queue("tmp", "inbox")
        descriptor, temp_path = tempfile.mkstemp(dir=queue_dir("tmp"), suffix=".json")
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        name = f"{time.time_ns():020d}-{service}-{os.getpid()}.json"
        os.replace(temp_path, queue_dir("inbox") / name)
        return True
    except OSError as error:
        print(f"notify: could not queue message: {error}", file=sys.stderr)
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)
        return False


def progress(
    title: str,
    message: str,
    percent: int,
    *,
    urgency: str = "normal",
    icon: str | None = None,
    timeout: int = 0,
    replace_id: int | None = None,
    dry_run: bool = False,
) -> None:
    if process.command_exists("dunstify"):
        args = [
            "dunstify",
            title,
            message,
            "-u",
            urgency,
            "-t",
            str(timeout),
            "-h",
            f"int:value:{percent}",
        ]
        if replace_id is not None:
            args.extend(["-r", str(replace_id)])
        if icon:
            args.extend(["-i", icon])
        process.run(args, dry_run=dry_run, quiet=True)
        return

    notify(
        title,
        message,
        urgency=urgency,
        icon=icon,
        timeout=timeout,
        replace_id=replace_id,
        dry_run=dry_run,
    )
