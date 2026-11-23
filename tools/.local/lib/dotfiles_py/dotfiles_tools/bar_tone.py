"""Is what shows behind the bar light or dark?

Waybar's own window is transparent and its pills are a light black tint
(`@define-color background rgba(…, 0.2)`), so what sits behind a module is whatever
the compositor draws under the bar: wallpaper, blur, anything. Rather than guess
from the wallpaper file, this samples the real pixels in the bar's top margin,
above the pills, with `grim` (a few milliseconds), darkens them by the pills'
tint, and calls the result "light" when the bar's accent colours would fall below
3:1 contrast on it, the WCAG minimum for UI text.
"""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

from .paths import xdg_config_home

DEFAULT_ALPHA = 0.2
ACCENTS = ("#8fd694", "#f5c542")  # the Hubstaff module's tracking/paused text colours
MIN_CONTRAST = 3.0
SAMPLE_ROWS = (1, 3)  # inside the bar's 5px top margin, above every pill


def bar_alpha(colors_css: Path | None = None) -> float:
    """The pill opacity Wallust writes into Waybar's colors.css."""
    path = colors_css or xdg_config_home() / "waybar" / "colors.css"
    try:
        match = re.search(r"@define-color background rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*([\d.]+)\s*\)", path.read_text())
    except OSError:
        match = None
    return float(match.group(1)) if match else DEFAULT_ALPHA


def _linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def luminance(hex_colour: str) -> float:
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * _linear(r) + 0.7152 * _linear(g) + 0.0722 * _linear(b)


def contrast(a: float, b: float) -> float:
    high, low = max(a, b), min(a, b)
    return (high + 0.05) / (low + 0.05)


def tone_for(grey: float, alpha: float) -> tuple[str, float]:
    """Classify a backdrop's mean sRGB grey (0-1) under a black tint of opacity `alpha`."""
    behind = _linear((1 - alpha) * grey)
    worst = min(contrast(luminance(colour), behind) for colour in ACCENTS)
    return ("light" if worst < MIN_CONTRAST else "dark"), worst


def mean_grey(ppm: bytes) -> float:
    """Mean sRGB grey (Rec. 709 weights, 0-1) of a binary PPM (P6) image."""
    header = re.match(rb"P6\s+(\d+)\s+(\d+)\s+(\d+)\s", ppm)
    if not header:
        raise ValueError("not a P6 PPM image")
    width, height, maxval = (int(value) for value in header.groups())
    pixels = ppm[header.end():header.end() + width * height * 3]
    if maxval != 255 or len(pixels) < width * height * 3 or not pixels:
        raise ValueError("unsupported or truncated PPM")
    r, g, b = sum(pixels[0::3]), sum(pixels[1::3]), sum(pixels[2::3])
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / (255 * width * height)


_MONITOR_TTL = 30.0
_monitor_cache: tuple[float, dict | None] = (float("-inf"), None)


def _bar_monitor() -> dict | None:
    """The focused monitor's geometry, re-read at most every 30s (it rarely changes)."""
    global _monitor_cache
    fetched_at, cached = _monitor_cache
    if cached is not None and time.monotonic() - fetched_at < _MONITOR_TTL:
        return cached
    try:
        monitors = json.loads(subprocess.run(["hyprctl", "-j", "monitors"], capture_output=True, text=True, timeout=3).stdout)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
    focused = [m for m in monitors if m.get("focused")]
    monitor = (focused or monitors or [None])[0]
    _monitor_cache = (time.monotonic(), monitor)
    return monitor


def sample(span: tuple[float, float] = (0.5, 1.0)) -> float | None:
    """Mean grey behind the bar over a horizontal span (fractions of the monitor width)."""
    monitor = _bar_monitor()
    if not monitor:
        return None
    x0 = monitor["x"] + int(monitor["width"] * span[0])
    width = max(1, int(monitor["width"] * (span[1] - span[0])))
    top, bottom = SAMPLE_ROWS
    geometry = f"{x0},{monitor['y'] + top} {width}x{bottom - top + 1}"
    try:
        completed = subprocess.run(["grim", "-g", geometry, "-t", "ppm", "-"], capture_output=True, timeout=3)
        return mean_grey(completed.stdout) if completed.returncode == 0 else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def current(span: tuple[float, float] = (0.5, 1.0)) -> str:
    """'light' or 'dark' behind the given span of the bar; 'dark' when it cannot be sampled.

    The default span is the right half, where Waybar's right-hand modules sit.
    """
    grey = sample(span)
    return "dark" if grey is None else tone_for(grey, bar_alpha())[0]
