"""Compatibility adapter for controlling legacy and Lua Hyprland sessions."""

from __future__ import annotations

import json

from . import process
from .paths import xdg_config_home


def uses_lua_config() -> bool:
    return (xdg_config_home() / "hypr" / "hyprland.lua").is_file()


def eval_lua(code: str, *, dry_run: bool = False) -> int:
    return process.run(["hyprctl", "eval", code], dry_run=dry_run).returncode


def monitor(*, output: str, mode: str | None = None, position: str | None = None, scale: float | str | None = None, vrr: int | None = None, dry_run: bool = False) -> int:
    if not uses_lua_config():
        if vrr is not None:
            return process.run(["hyprctl", "keyword", "misc:vrr", str(vrr)], dry_run=dry_run).returncode
        assert mode is not None and position is not None and scale is not None
        return process.run(["hyprctl", "keyword", "monitor", f"{output},{mode},{position},{scale}"], dry_run=dry_run).returncode

    fields = {"output": output}
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
    if not uses_lua_config():
        return process.run(["hyprctl", "dispatch", "movetoworkspacesilent", f"{workspace},{selector}"], dry_run=dry_run).returncode
    return eval_lua(
        "hl.dispatch(hl.dsp.window.move({ "
        f"workspace = {json.dumps(workspace)}, follow = false, window = {json.dumps(selector)} "
        "}))",
        dry_run=dry_run,
    )
