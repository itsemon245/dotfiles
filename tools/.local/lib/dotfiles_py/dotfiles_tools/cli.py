"""Small CLI helpers for dotfiles tools."""

from __future__ import annotations

import argparse
import sys
from typing import NoReturn


class ToolError(RuntimeError):
    """Expected command-line failure."""


def add_dry_run(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print intended commands without changing system state",
    )


def die(message: str, status: int = 1) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(status)


def main_with_errors(func) -> int:
    try:
        return int(func() or 0)
    except ToolError as exc:
        die(str(exc))

