"""Rofi menu helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable

from .cli import ToolError
from .process import require


def entry(label: str, icon: str | None = None) -> str:
    if icon:
        return f"{label}\0icon\x1f{icon}"
    return label


def dmenu(
    rows: Iterable[str],
    *,
    prompt: str,
    theme: str | Path | None = None,
    mesg: str | None = None,
    markup_rows: bool = False,
    selected_row: int | None = None,
    extra_args: list[str] | None = None,
) -> str | None:
    require("rofi")
    args = ["rofi", "-dmenu", "-i", "-p", prompt]
    if mesg:
        args.extend(["-mesg", mesg])
    if theme:
        args.extend(["-theme", str(theme)])
    if markup_rows:
        args.append("-markup-rows")
    if selected_row is not None:
        args.extend(["-selected-row", str(selected_row)])
    if extra_args:
        args.extend(extra_args)

    data = "\n".join(rows) + "\n"
    completed = subprocess.run(args, input=data, text=True, stdout=subprocess.PIPE)
    if completed.returncode != 0:
        return None
    selected = completed.stdout.rstrip("\n")
    return selected or None


def dmenu_index(
    rows: Iterable[str],
    *,
    prompt: str,
    theme: str | Path | None = None,
    selected_row: int | None = None,
    extra_args: list[str] | None = None,
) -> int | None:
    selected = dmenu(
        rows,
        prompt=prompt,
        theme=theme,
        selected_row=selected_row,
        extra_args=["-format", "i", *(extra_args or [])],
    )
    if selected is None:
        return None
    try:
        return int(selected)
    except ValueError as exc:
        raise ToolError(f"invalid rofi selection: {selected}") from exc

