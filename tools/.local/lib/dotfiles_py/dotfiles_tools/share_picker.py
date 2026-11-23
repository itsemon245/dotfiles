"""Screen-share picker for xdg-desktop-portal-hyprland that stops repeat prompts.

Chrome and Electron apps (Meet, Slack) open several portal sessions for one share:
one per tab of their own picker plus one for the real stream. Each session runs the
picker again, so one share asks 2-4 times. This wrapper runs the real
hyprland-share-picker once and, for a few seconds afterwards, answers repeat
requests with the same choice without showing anything.

xdph runs the picker with the share lists in XDPH_* variables (plus --allow-token
when the app supports "remember") and reads one line back:
`[SELECTION]<flags>/<type>:<value>`, e.g. `[SELECTION]r/screen:DP-2`, where the
flag `r` asks for a restore token.

A remembered choice is reused only while it is fresh (SHARE_PICKER_REUSE_SECONDS,
default 15) and only if its monitor or window is still offered. Cancelling is
never remembered.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REAL_PICKER = "/usr/bin/hyprland-share-picker"
PREFIX = "[SELECTION]"
DEFAULT_REUSE_SECONDS = 15.0

LISTS_BY_TYPE = {
    "screen": ("XDPH_OUTPUT_SHARING_LIST",),
    "window": ("XDPH_WINDOW_SHARING_LIST",),
    "workspace": ("XDPH_WORKSPACE_SHARING_LIST_V3", "XDPH_WORKSPACE_SHARING_LIST_V2", "XDPH_WORKSPACE_SHARING_LIST"),
}


def cache_file() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    return Path(runtime) / "share-picker" / "last.json"


def reuse_seconds() -> float:
    try:
        return float(os.environ.get("SHARE_PICKER_REUSE_SECONDS", DEFAULT_REUSE_SECONDS))
    except ValueError:
        return DEFAULT_REUSE_SECONDS


def parse(selection: str) -> tuple[str, str, str] | None:
    """Split `[SELECTION]flags/type:value` into (flags, type, value)."""
    if not selection.startswith(PREFIX) or "/" not in selection:
        return None
    flags, _, target = selection[len(PREFIX):].partition("/")
    kind, sep, value = target.partition(":")
    if not sep:
        return None
    return flags, kind, value


def still_offered(kind: str, value: str, env: dict[str, str]) -> bool:
    """A region is always valid; a monitor/window/workspace must still be in xdph's list."""
    if kind == "region":
        return True
    names = LISTS_BY_TYPE.get(kind)
    if not names:
        return False
    return any(value and value in env.get(name, "") for name in names)


def adapt(selection: str, *, allow_token: bool) -> str:
    """Drop the remember flag when this request did not offer one."""
    parsed = parse(selection)
    if parsed is None or allow_token:
        return selection
    flags, kind, value = parsed
    return f"{PREFIX}{flags.replace('r', '')}/{kind}:{value}"


def load_recent(path: Path, now: float, window: float) -> tuple[str, float] | None:
    """Return (selection, age in seconds) when the last choice is younger than `window`."""
    try:
        data = json.loads(path.read_text())
        age = now - float(data["time"])
        selection = data["selection"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if not isinstance(selection, str) or not 0 <= age <= window:
        return None
    return selection, age


def save(path: Path, selection: str, now: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"time": now, "selection": selection}))
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    env = dict(os.environ)
    allow_token = "--allow-token" in args
    path = cache_file()
    now = time.time()

    recent = load_recent(path, now, reuse_seconds())
    if recent:
        selection, age = recent
        parsed = parse(selection)
        if parsed and still_offered(parsed[1], parsed[2], env):
            print(f"share-picker: reusing {parsed[1]}:{parsed[2]} chosen {age:.0f}s ago", file=sys.stderr)
            print(adapt(selection, allow_token=allow_token), flush=True)
            return 0

    completed = subprocess.run([REAL_PICKER, *args], stdout=subprocess.PIPE, text=True)
    output = completed.stdout
    selection = next((line.strip() for line in output.splitlines() if line.startswith(PREFIX)), None)
    if selection and parse(selection):
        save(path, selection, time.time())
    sys.stdout.write(output)
    sys.stdout.flush()
    return completed.returncode
