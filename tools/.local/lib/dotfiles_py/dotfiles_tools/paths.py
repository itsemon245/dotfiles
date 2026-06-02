"""XDG and home path helpers."""

from __future__ import annotations

import os
from pathlib import Path


def home() -> Path:
    return Path(os.environ.get("HOME", str(Path.home()))).expanduser()


def xdg_cache_home() -> Path:
    return Path(os.environ.get("XDG_CACHE_HOME", home() / ".cache")).expanduser()


def xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", home() / ".config")).expanduser()


def cache_dir(name: str) -> Path:
    path = xdg_cache_home() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def expand(path: str | Path) -> Path:
    return Path(path).expanduser()

