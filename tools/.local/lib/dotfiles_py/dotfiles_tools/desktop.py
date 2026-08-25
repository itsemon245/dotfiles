"""Desktop utility commands."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from textwrap import dedent

from . import hypr_runtime, notify, process, rofi
from .cli import ToolError, add_dry_run
from .paths import cache_dir, home, xdg_config_home


def _parser(prog: str, description: str) -> argparse.ArgumentParser:
    return argparse.ArgumentParser(prog=prog, description=description)


def _backlight_device() -> str | None:
    text = process.output(["brightnessctl", "-l"])
    pattern = re.compile(r"Device '([^']+)' of class '([^']+)'", re.IGNORECASE)
    for line in text.splitlines():
        match = pattern.search(line)
        if not match:
            continue
        name, device_class = match.groups()
        haystack = f"{name} {device_class}".lower()
        if any(token in haystack for token in ("backlight", "acpi_video", "intel_backlight", "amdgpu_bl")):
            return name
    return None


def _brightness_value(args: list[str]) -> str:
    completed = process.run(args, capture=True)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def main_brightness(argv: list[str] | None = None) -> int:
    parser = _parser("brightness", "Print current brightness as Waybar JSON.")
    parser.parse_args(argv)
    if not process.command_exists("brightnessctl"):
        return 0

    device = _backlight_device()
    base = ["brightnessctl"]
    if device:
        base.extend(["-d", device])

    current = _brightness_value([*base, "get"])
    maximum = _brightness_value([*base, "max"])
    if not current.isdigit() or not maximum.isdigit() or int(maximum) <= 0:
        return 0

    percent = int(int(current) * 100 / int(maximum))
    print(json.dumps({"text": str(percent), "percentage": percent, "class": "backlight"}))
    return 0


def main_brightness_adjust(argv: list[str] | None = None) -> int:
    parser = _parser("brightness-adjust", "Adjust screen brightness.")
    parser.add_argument("direction", nargs="?", default="+", choices=["+", "-"])
    parser.add_argument("amount", nargs="?", default="5")
    add_dry_run(parser)
    args = parser.parse_args(argv)
    process.require("brightnessctl")

    command = ["brightnessctl"]
    device = _backlight_device()
    if device:
        command.extend(["-d", device])
    command.extend(["set", f"{args.direction}{args.amount}%"])
    return process.run(command, dry_run=args.dry_run).returncode


def main_disk_free(argv: list[str] | None = None) -> int:
    parser = _parser("disk-free", "Print available local disk space in GiB.")
    parser.parse_args(argv)
    completed = process.run(["df", "-l", "-B1"], capture=True)
    if completed.returncode != 0:
        return completed.returncode

    total = 0
    for line in completed.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 6:
            continue
        filesystem, available, mountpoint = parts[0], parts[3], parts[5]
        if not filesystem.startswith("/dev/") or mountpoint in {"/boot", "/boot/efi"}:
            continue
        if available.isdigit():
            total += int(available)
    print(f"{total / 1024 / 1024 / 1024:.2f}G")
    return 0


def _rofi_theme(*parts: str) -> Path:
    return xdg_config_home() / "rofi" / Path(*parts)


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() not in {"0", "false", "no", "off"}


def _env_path(name: str, default: Path) -> Path:
    return Path(os.environ.get(name, str(default))).expanduser()


def _positive_int(value: str, name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ToolError(f"{name} must be an integer") from exc
    if parsed <= 0:
        raise ToolError(f"{name} must be greater than zero")
    return parsed


def _notify_cast(message: str, urgency: str = "normal", *, dry_run: bool = False) -> None:
    notify.notify("scrcpy", message, urgency=urgency, icon="phone", replace_id=992033, dry_run=dry_run)


def _detect_adb_port(phone_ip: str, *, service: str, timeout_seconds: int) -> str | None:
    if not (process.command_exists("timeout") and process.command_exists("avahi-browse")):
        return None
    completed = process.run(
        ["timeout", str(timeout_seconds), "avahi-browse", "-rpt", service],
        capture=True,
    )
    if completed.returncode != 0:
        return None
    for line in completed.stdout.splitlines():
        if not line.startswith("="):
            continue
        parts = line.split(";")
        if len(parts) > 8 and parts[7] == phone_ip:
            return parts[8]
    return None


def _adb_connect(phone_ip: str, port: str) -> bool:
    process.run(["adb", "kill-server"])
    time.sleep(0.3)
    process.run(["adb", "disconnect", phone_ip])
    result = process.output(["adb", "connect", f"{phone_ip}:{port}"])
    if "connected to" not in result:
        return False
    state = process.output(["adb", "-s", f"{phone_ip}:{port}", "get-state"]).strip()
    return state == "device"


def _cast_modes() -> dict[str, list[str]]:
    return {
        "Cast": ["--no-audio"],
        "Cast + PC Audio": ["--audio-buffer=200", "--audio-bit-rate=256K"],
        "Cast + Screen Off": ["--no-audio", "--stay-awake", "--turn-screen-off"],
        "Cast + Screen Off + PC Audio": [
            "--stay-awake",
            "--turn-screen-off",
            "--audio-buffer=200",
            "--audio-bit-rate=256K",
        ],
    }


def main_rofi_cast(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="rofi-cast",
        description="Connect to Android wireless debugging and launch scrcpy.",
        epilog=dedent(
            """\
            Examples:
              rofi-cast
              rofi-cast --theme ~/.config/rofi/cast.rasi
              rofi-cast --mode "Cast" --port 37123
              rofi-cast --mode "Cast" --port 37123 --perf-flags="--max-size=1200 --max-fps=60"
            """
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--phone-ip", default=os.environ.get("ROFI_CAST_PHONE_IP", "192.168.0.222"))
    parser.add_argument("--phone-name", default=os.environ.get("ROFI_CAST_PHONE_NAME", "Pocophone F1"))
    parser.add_argument(
        "--theme",
        type=Path,
        default=_env_path("ROFI_CAST_THEME", _rofi_theme("applets", "type-1", "style-1.rasi")),
        help="Rofi theme path for mode and port prompts",
    )
    parser.add_argument(
        "--mode",
        default=os.environ.get("ROFI_CAST_MODE"),
        help="cast mode to run directly; omit to choose with Rofi",
    )
    parser.add_argument("--port", default=os.environ.get("ROFI_CAST_PORT"), help="ADB wireless debugging port")
    parser.add_argument(
        "--detect",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("ROFI_CAST_DETECT", True),
        help="detect the ADB port with avahi-browse before prompting",
    )
    parser.add_argument(
        "--detect-timeout",
        default=os.environ.get("ROFI_CAST_DETECT_TIMEOUT", "5"),
        help="ADB service discovery timeout in seconds",
    )
    parser.add_argument(
        "--adb-service",
        default=os.environ.get("ROFI_CAST_ADB_SERVICE", "_adb-tls-connect._tcp"),
        help="Avahi service name for Android wireless debugging",
    )
    parser.add_argument(
        "--perf-flags",
        metavar="FLAGS",
        default=os.environ.get(
            "ROFI_CAST_PERF_FLAGS",
            "--video-bit-rate=6M --max-fps=30 --video-buffer=150 --video-codec=h265 --max-size=1600 --shortcut-mod=lctrl",
        ),
        help="quoted scrcpy performance flags; use --perf-flags=... when the value starts with --",
    )
    parser.add_argument(
        "--scrcpy-args",
        metavar="ARGS",
        default=os.environ.get("ROFI_CAST_SCRCPY_ARGS", ""),
        help="quoted extra scrcpy arguments appended after the selected mode; use --scrcpy-args=... when needed",
    )
    add_dry_run(parser)
    args = parser.parse_args(argv)
    modes = _cast_modes()
    theme = Path(args.theme).expanduser()
    detect_timeout = _positive_int(args.detect_timeout, "detect timeout")
    if args.mode and args.mode not in modes:
        raise ToolError("unknown cast mode; expected one of: " + ", ".join(modes))
    if not args.dry_run:
        process.require("adb", "scrcpy")
    if not args.mode:
        process.require("rofi")

    perf_flags = shlex.split(args.perf_flags)
    extra_scrcpy_args = shlex.split(args.scrcpy_args)

    chosen = args.mode or rofi.dmenu(
        modes.keys(),
        prompt="Cast",
        theme=theme,
        mesg=f"{args.phone_name} - {args.phone_ip}",
        selected_row=0,
        extra_args=[
            "-theme-str",
            'textbox-prompt-colon {str: ">";}',
        ],
    )
    if not chosen:
        return 0

    port = args.port
    if not port and args.detect:
        _notify_cast("Detecting ADB port...", dry_run=args.dry_run)
        port = _detect_adb_port(args.phone_ip, service=args.adb_service, timeout_seconds=detect_timeout)
    if not port:
        process.require("rofi")
        port = rofi.dmenu([""], prompt="ADB port (check phone):", theme=theme)
    if not port:
        return 0

    _notify_cast(f"Connecting to {args.phone_ip}:{port}...", dry_run=args.dry_run)
    if not args.dry_run and not _adb_connect(args.phone_ip, port):
        time.sleep(1)
        if not _adb_connect(args.phone_ip, port):
            _notify_cast(f"ADB connect failed ({args.phone_ip}:{port})", "critical", dry_run=args.dry_run)
            return 1

    _notify_cast(f"Casting {args.phone_name}...", dry_run=args.dry_run)
    command = ["scrcpy", "--window-title", args.phone_name, *perf_flags, *modes[chosen], *extra_scrcpy_args]
    try:
        return process.run(command, dry_run=args.dry_run).returncode
    finally:
        process.run(["adb", "disconnect", args.phone_ip], dry_run=args.dry_run)
        _notify_cast("Cast ended.", dry_run=args.dry_run)


def _first_monitor() -> dict:
    process.require("hyprctl")
    completed = process.run(["hyprctl", "monitors", "-j"], capture=True)
    if completed.returncode != 0:
        raise ToolError("could not get monitor info")
    monitors = json.loads(completed.stdout)
    if not monitors:
        raise ToolError("could not get monitor info")
    return monitors[0]


def _available_rates(monitor: dict, resolution: str) -> list[int]:
    rates = set()
    for mode in monitor.get("availableModes", []):
        if not mode.startswith(resolution + "@"):
            continue
        value = mode.split("@", 1)[1].removesuffix("Hz")
        try:
            rates.add(int(float(value)))
        except ValueError:
            continue
    preferred = [180, 144, 120, 60]
    preferred_rates = [rate for rate in preferred if rate in rates]
    return preferred_rates or sorted(rates, reverse=True)


def _monitor_message(monitor: dict) -> str:
    resolution = f"{monitor.get('width')}x{monitor.get('height')}"
    current_rate = int(float(monitor.get("refreshRate", 0)))
    vrr_label = "ON" if monitor.get("vrr") else "OFF"
    return f"{monitor.get('name')} - {resolution} - {current_rate}Hz - VRR: {vrr_label}"


def main_rofi_monitor(argv: list[str] | None = None) -> int:
    parser = _parser("rofi-monitor", "Switch monitor refresh rate or toggle VRR.")
    add_dry_run(parser)
    args = parser.parse_args(argv)
    process.require("hyprctl", "rofi")

    monitor = _first_monitor()
    resolution = f"{monitor.get('width')}x{monitor.get('height')}"
    current_rate = int(float(monitor.get("refreshRate", 0)))
    rates = _available_rates(monitor, resolution)
    rows = [f"  {rate}Hz  *" if rate == current_rate else f"  {rate}Hz" for rate in rates]
    rows.append("")
    rows.append("  VRR  ON" if monitor.get("vrr") else "  VRR  OFF")

    chosen = rofi.dmenu(
        rows,
        prompt="Monitor",
        theme=_rofi_theme("applets", "type-1", "style-1.rasi"),
        mesg=_monitor_message(monitor),
        markup_rows=True,
        selected_row=0,
        extra_args=[
            "-theme-str",
            "window {width: 400px;}",
            "-theme-str",
            f"listview {{columns: 1; lines: {len(rows)};}}",
            "-theme-str",
            'textbox-prompt-colon {str: ">";}',
        ],
    )
    if not chosen:
        return 0
    chosen = chosen.strip()

    if "VRR" in chosen:
        target = 0 if monitor.get("vrr") else 1
        status = hypr_runtime.monitor(output=str(monitor.get("name")), vrr=target, dry_run=args.dry_run)
        notify.notify("Monitor", "VRR Disabled" if target == 0 else "VRR Enabled (Adaptive Sync)")
        return status

    match = re.search(r"(\d+)Hz", chosen)
    if not match:
        return 0
    rate = match.group(1)
    name = str(monitor.get("name"))
    scale = str(monitor.get("scale"))
    position = f"{monitor.get('x')}x{monitor.get('y')}"
    status = hypr_runtime.monitor(
        output=name,
        mode=f"{resolution}@{rate}",
        position=position,
        scale=scale,
        dry_run=args.dry_run,
    )
    notify.notify("Monitor", f"Switched to {rate}Hz" if status == 0 else f"Failed to switch to {rate}Hz")
    return status


def _active_bar() -> str | None:
    if process.pgrep("-x", "ironbar"):
        return "ironbar"
    for bar in ("waybar",):
        if process.pgrep("-x", bar):
            return bar
    return None


def _bar_configs() -> dict[str, dict[str, list[str]]]:
    config_home = os.environ.get("XDG_CONFIG_HOME", str(home() / ".config"))
    return {
        "waybar": {
            "compile": [
                "sass",
                "--style=compressed",
                f"{config_home}/waybar/style.scss",
                f"{config_home}/waybar/style.css",
            ],
            "cmd": ["waybar"],
        },
        "ironbar": {
            "compile": [
                "sass",
                f"{config_home}/themes/shared/vars.scss",
                f"{config_home}/themes/shared/vars.css",
            ],
            "cmd": ["ironbar"],
        },
    }


def _kill_bar(bar: str, dry_run: bool = False) -> None:
    if process.pgrep("-x", bar):
        print(f"Killing {bar}...")
        process.pkill("-x", bar, dry_run=dry_run)
    else:
        print(f"{bar} is not running.")


def _start_bar(dry_run: bool = False) -> int:
    configs = _bar_configs()
    target = _active_bar() or os.environ.get("DEFAULT_BAR", "waybar")
    if target not in configs:
        target = "waybar"
    print(f"Active target: {target}")

    compile_cmd = configs[target]["compile"]
    if compile_cmd:
        process.require(compile_cmd[0])
        print(f"Compiling for {target}...")
        result = process.run(compile_cmd, dry_run=dry_run)
        if result.returncode != 0:
            return result.returncode

    for bar in configs:
        if bar != target and process.pgrep("-x", bar):
            print(f"Killing {bar}...")
            process.pkill("-x", bar, dry_run=dry_run)

    print(f"Reloading {target}...")
    process.pkill("-x", target, dry_run=dry_run)
    process.background(configs[target]["cmd"], dry_run=dry_run)
    print("Done.")
    return 0


def main_barr(argv: list[str] | None = None) -> int:
    parser = _parser("barr", "Compile and reload the active status bar.")
    parser.add_argument("-k", "--kill", nargs="?", const="", metavar="NAME")
    parser.add_argument("--kill-all", action="store_true")
    parser.add_argument("-t", "--toggle", action="store_true")
    add_dry_run(parser)
    args = parser.parse_args(argv)

    configs = _bar_configs()
    if args.kill_all:
        print("Killing all bars...")
        for bar in configs:
            _kill_bar(bar, args.dry_run)
        return 0

    if args.kill is not None:
        target = args.kill or _active_bar()
        if target:
            _kill_bar(target, args.dry_run)
        else:
            print("No active bar to kill.")
        return 0

    if args.toggle:
        active = _active_bar()
        if active:
            _kill_bar(active, args.dry_run)
            print("Toggled off.")
            return 0
        return _start_bar(args.dry_run)

    return _start_bar(args.dry_run)


def main_readable_window(argv: list[str] | None = None) -> int:
    parser = _parser("readable-window", "Toggle Hyprland readability mode.")
    parser.add_argument("--active-window", action="store_true", help="toggle only the active window")
    parser.add_argument("--lock-file", default="/tmp/hypr_focus_mode_active")
    add_dry_run(parser)
    args = parser.parse_args(argv)
    process.require("hyprctl")

    if args.active_window:
        lock = Path(args.lock_file)
        if lock.exists():
            if args.dry_run:
                print(f"+ remove {lock}")
            else:
                lock.unlink()
            process.run(["hyprctl", "reload"], dry_run=args.dry_run)
            notify.notify("Hyprland", "Window visual effects reset.", icon="view-refresh", replace_id=9999)
            return 0

        completed = process.run(["hyprctl", "activewindow", "-j"], capture=True)
        if completed.returncode != 0:
            return completed.returncode
        address = json.loads(completed.stdout).get("address")
        if not address or address == "null":
            notify.notify("Hyprland", "No active window selected.")
            return 0
        if args.dry_run:
            print(f"+ touch {lock}")
        else:
            lock.touch()
        if hypr_runtime.uses_lua_config():
            selector = f"address:{address}"
            hypr_runtime.eval_lua(
                "hl.dispatch(hl.dsp.window.set_prop({ "
                "prop = 'opacity', value = '1.0 override 1.0 override', "
                f"window = {json.dumps(selector)} "
                "}))",
                dry_run=args.dry_run,
            )
            hypr_runtime.eval_lua(
                "hl.dispatch(hl.dsp.window.set_prop({ "
                "prop = 'no_blur', value = true, "
                f"window = {json.dumps(selector)} "
                "}))",
                dry_run=args.dry_run,
            )
        else:
            process.run(
                ["hyprctl", "keyword", "windowrulev2", f"opacity 1 override 1 override, address:{address}"],
                dry_run=args.dry_run,
            )
            process.run(["hyprctl", "keyword", "windowrulev2", f"noblur, address:{address}"], dry_run=args.dry_run)
        notify.notify("Hyprland", "Active window is now solid.", icon="video-display", replace_id=9999)
        return 0

    completed = process.run(["hyprctl", "getoption", "decoration:blur:enabled", "-j"], capture=True)
    if completed.returncode != 0:
        return completed.returncode
    enabled = json.loads(completed.stdout).get("int") == 1
    if enabled:
        if hypr_runtime.uses_lua_config():
            hypr_runtime.eval_lua(
                "hl.config({ decoration = { blur = { enabled = false }, active_opacity = 1.0, inactive_opacity = 1.0 }, "
                "general = { col = { active_border = 'rgba(00ff00ee)' } } })",
                dry_run=args.dry_run,
            )
        else:
            for command in (
                ["hyprctl", "keyword", "decoration:blur:enabled", "false"],
                ["hyprctl", "keyword", "decoration:active_opacity", "1.0"],
                ["hyprctl", "keyword", "decoration:inactive_opacity", "1.0"],
                ["hyprctl", "keyword", "general:col.active_border", "rgba(00ff00ee)"],
            ):
                process.run(command, dry_run=args.dry_run)
        notify.notify("Hyprland", "Opacity: 1.0 | Blur: 0", icon="video-display", replace_id=9999)
    else:
        process.run(["hyprctl", "reload"], dry_run=args.dry_run)
        notify.notify("Hyprland", "Restored from config", icon="video-display", replace_id=9999)
    return 0


def main_cliphist_rofi(argv: list[str] | None = None) -> int:
    parser = _parser("cliphist-rofi", "Show cliphist entries in Rofi and copy the selected item.")
    parser.parse_args(argv)
    process.require("cliphist", "rofi", "wl-copy")

    preview_dir = cache_dir("cliphist-previews")
    cutoff = time.time() - 3600
    for file in preview_dir.iterdir():
        try:
            if file.is_file() and file.stat().st_mtime < cutoff:
                file.unlink()
        except OSError:
            pass

    entries_text = process.output(["cliphist", "list"])
    rows: list[str] = []
    hashes: list[str] = []
    preview_map: dict[int, Path] = {}

    for line in entries_text.splitlines():
        if "\t" in line:
            item_hash, content = line.split("\t", 1)
        else:
            item_hash, content = line, line
        hashes.append(item_hash)
        image_info = _cliphist_image_info(item_hash)
        if image_info:
            preview = _cliphist_thumbnail(item_hash, preview_dir)
            if preview:
                preview_map[len(rows)] = preview
            rows.append(f"[image] {image_info or content}")
        else:
            rows.append(content)

    if not rows:
        return 0

    for index, preview in preview_map.items():
        (preview_dir / f"map_{index}.txt").write_text(str(preview), encoding="utf-8")

    modi_script = preview_dir / "cliphist-modi.sh"
    modi_script.write_text(
        """#!/usr/bin/env bash
PREVIEW_DIR="${HOME}/.cache/cliphist-previews"
case "$1" in
  list) cat ;;
  info)
    if [[ -n "${ROFI_INFO:-}" && -f "$PREVIEW_DIR/map_${ROFI_INFO}.txt" ]]; then
      cat "$PREVIEW_DIR/map_${ROFI_INFO}.txt"
    fi
    ;;
esac
""",
        encoding="utf-8",
    )
    modi_script.chmod(0o755)

    data = "\n".join(rows) + "\n"
    completed = subprocess.run(
        [
            "rofi",
            "-modi",
            f"clipboard:{modi_script}",
            "-show",
            "clipboard",
            "-theme",
            str(_rofi_theme("launchers", "type-4", "style-6-clipboard.rasi")),
            "-dmenu",
            "-i",
            "-p",
            "Clipboard",
            "-format",
            "i",
            "-selected-row",
            "0",
        ],
        input=data,
        text=True,
        stdout=subprocess.PIPE,
    )
    for file in preview_dir.glob("map_*.txt"):
        file.unlink(missing_ok=True)
    if completed.returncode != 0:
        return 0
    selected = completed.stdout.strip()
    if not selected.isdigit():
        return 0
    index = int(selected)
    if index < 0 or index >= len(hashes):
        return 0

    decoded = subprocess.run(["cliphist", "decode", hashes[index]], stdout=subprocess.PIPE, check=False)
    if decoded.returncode != 0:
        return decoded.returncode
    return subprocess.run(["wl-copy"], input=decoded.stdout).returncode


def _cliphist_decode_bytes(item_hash: str) -> bytes | None:
    completed = subprocess.run(["cliphist", "decode", item_hash], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if completed.returncode != 0:
        return None
    return completed.stdout


def _cliphist_image_info(item_hash: str) -> str | None:
    if not process.command_exists("file"):
        return None
    data = _cliphist_decode_bytes(item_hash)
    if data is None:
        return None
    completed = subprocess.run(["file", "-"], input=data, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    text = completed.stdout.decode(errors="replace")
    if not re.search(r"(image|PNG|JPEG|GIF|WebP)", text, re.IGNORECASE):
        return None
    return text.split(":", 1)[-1].strip()


def _cliphist_thumbnail(item_hash: str, preview_dir: Path) -> Path | None:
    converter = "magick" if process.command_exists("magick") else "convert" if process.command_exists("convert") else None
    if not converter:
        return None
    preview = preview_dir / f"{item_hash}.png"
    if preview.exists():
        return preview
    data = _cliphist_decode_bytes(item_hash)
    if data is None:
        return None
    command = [converter, "-", "-resize", "200x200>", "-quality", "90", str(preview)]
    completed = subprocess.run(command, input=data, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return preview if completed.returncode == 0 and preview.exists() else None
