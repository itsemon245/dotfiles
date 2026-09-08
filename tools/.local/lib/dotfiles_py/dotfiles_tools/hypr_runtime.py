"""Runtime adapter for controlling the Lua Hyprland session."""

from __future__ import annotations

import argparse
import json

from . import process
from .cli import add_dry_run


def eval_lua(code: str, *, dry_run: bool = False) -> int:
    return process.run(["hyprctl", "eval", code], dry_run=dry_run).returncode


def monitor(*, output: str, mode: str | None = None, position: str | None = None, scale: float | str | None = None, vrr: int | None = None, dry_run: bool = False) -> int:
    fields: dict[str, str | float | int] = {"output": output}
    if mode is not None:
        fields["mode"] = mode
    if position is not None:
        fields["position"] = position
    if scale is not None:
        fields["scale"] = scale
    if vrr is not None:
        fields["vrr"] = vrr
    lua_fields = ", ".join(f"{key} = {json.dumps(value)}" for key, value in fields.items())
    return eval_lua(f"hl.monitor({{{lua_fields}}})", dry_run=dry_run)


def move_window(*, workspace: str, selector: str, dry_run: bool = False) -> int:
    return eval_lua(
        "hl.dispatch(hl.dsp.window.move({ "
        f"workspace = {json.dumps(workspace)}, follow = false, window = {json.dumps(selector)} "
        "}))",
        dry_run=dry_run,
    )


def session_uses_uwsm() -> bool:
    """Return whether the current user manager owns a UWSM compositor unit."""
    if not process.command_exists("systemctl"):
        return False
    return process.run(
        ["systemctl", "--user", "is-active", "--quiet", "wayland-wm@*.service"],
        quiet=True,
    ).returncode == 0


def logout(*, dry_run: bool = False) -> int:
    """End the graphical session through its owning session manager."""
    if session_uses_uwsm():
        process.require("uwsm")
        return process.run(["uwsm", "stop"], dry_run=dry_run).returncode

    process.require("hyprctl")
    return eval_lua("hl.dispatch(hl.dsp.exit())", dry_run=dry_run)


def main_logout(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hypr-logout", description="End the current Hyprland session cleanly.")
    add_dry_run(parser)
    args = parser.parse_args(argv)
    return logout(dry_run=args.dry_run)
