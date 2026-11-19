"""Rofi power menu: lock, suspend, hibernate, log out, reboot, shut down."""

from __future__ import annotations

import argparse
import os
import shlex
from dataclasses import dataclass
from pathlib import Path

from . import hypr_runtime, process, rofi
from .cli import add_dry_run
from .paths import xdg_config_home


@dataclass(frozen=True)
class Action:
    key: str
    label: str
    glyph: str  # Icomoon Feather codepoint used by the rofi powermenu themes.
    confirm: bool


ACTIONS: tuple[Action, ...] = (
    Action("lock", "Lock", "", confirm=False),
    Action("suspend", "Suspend", "", confirm=False),
    Action("hibernate", "Hibernate", "", confirm=True),
    Action("logout", "Log out", "", confirm=True),
    Action("reboot", "Reboot", "", confirm=True),
    Action("shutdown", "Shut down", "", confirm=True),
)
ACTION_KEYS = tuple(action.key for action in ACTIONS)
YES, NO = "", ""

SYSTEMCTL_VERB = {"suspend": "suspend", "hibernate": "hibernate", "reboot": "reboot", "shutdown": "poweroff"}


def theme_dir() -> Path:
    override = os.environ.get("POWER_MENU_THEME_DIR")
    if override:
        return Path(override).expanduser()
    return xdg_config_home() / "rofi" / "powermenu" / "type-4"


def command_for(key: str, *, has_hyprshutdown: bool, uses_uwsm: bool) -> list[str] | None:
    """Return the command for an action, or None when it is handled in-process (logout)."""
    if key == "lock":
        return ["loginctl", "lock-session"]
    if key == "logout":
        return None
    verb = SYSTEMCTL_VERB[key]
    if key in ("reboot", "shutdown") and has_hyprshutdown and not uses_uwsm:
        # Let apps close (and save state) before the machine goes down.
        return ["hyprshutdown", "--post-cmd", shlex.join(["systemctl", verb])]
    return ["systemctl", verb]


def _uptime() -> str:
    try:
        seconds = int(float(Path("/proc/uptime").read_text().split()[0]))
    except (OSError, ValueError, IndexError):
        return "unknown"
    hours, minutes = divmod(seconds // 60, 60)
    days, hours = divmod(hours, 24)
    parts = [f"{days}d"] if days else []
    if days or hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def _pick(directory: Path) -> Action | None:
    index = rofi.dmenu_index(
        [action.glyph for action in ACTIONS],
        prompt=f"Goodbye {os.environ.get('USER', '')}".strip(),
        theme=directory / "style-1.rasi",
        extra_args=[
            "-mesg", f"Uptime: {_uptime()}",
            "-theme-str", f"listview {{columns: {len(ACTIONS)}; lines: 1;}}",
        ],
    )
    if index is None or not 0 <= index < len(ACTIONS):
        return None
    return ACTIONS[index]


def _confirmed(action: Action, directory: Path) -> bool:
    answer = rofi.dmenu(
        [YES, NO],
        prompt="Confirmation",
        theme=directory / "shared" / "confirm.rasi",
        mesg=f"{action.label}?",
    )
    return answer == YES


def run_action(key: str, *, dry_run: bool = False) -> int:
    uses_uwsm = hypr_runtime.session_uses_uwsm()
    if key == "logout":
        return hypr_runtime.logout(dry_run=dry_run)
    command = command_for(key, has_hyprshutdown=process.command_exists("hyprshutdown"), uses_uwsm=uses_uwsm)
    assert command is not None
    return process.run(command, dry_run=dry_run).returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="power-menu", description="Pick a session or power action with rofi.")
    parser.add_argument("action", nargs="?", choices=ACTION_KEYS, help="run this action directly, without the menu")
    parser.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    add_dry_run(parser)
    args = parser.parse_args(argv)

    if args.action:
        return run_action(args.action, dry_run=args.dry_run)

    directory = theme_dir()
    action = _pick(directory)
    if action is None:
        return 0
    if action.confirm and not args.yes and not _confirmed(action, directory):
        return 0
    return run_action(action.key, dry_run=args.dry_run)
