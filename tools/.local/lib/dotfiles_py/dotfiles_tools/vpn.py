"""WireGuard VPN manager for NetworkManager."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from textwrap import dedent

from . import notify, process, rofi
from .cli import ToolError
from .paths import home


VERSION = "3.1"
IMPORT_STRIP_PREFIX = "wg-"
NOTIF_ID = 992022
DRY_RUN = False
ICON_CONNECTED = "security-high"
ICON_DISCONNECTED = "network-vpn"
VPN_CONNECTED_MARKUP = "<span foreground='#00ff00' weight='bold'>󰞑</span>"


@dataclass
class FlagOptions:
    directory: Path | None = None
    cache_dir: Path = field(default_factory=lambda: home() / ".cache" / "rofi-vpn" / "flags")
    url_base: str = "https://flagcdn.com/w80/"
    emoji_fallback: bool = True
    download: bool = True


class State:
    def __init__(self, active: str, all_vpns: list[str], dry_run: bool, theme: Path, flags: FlagOptions) -> None:
        self.active = active
        self.all_vpns = all_vpns
        self.dry_run = dry_run
        self.theme = theme
        self.flags = flags


def _default_theme() -> Path:
    return Path(
        os.environ.get(
            "ROFI_VPN_THEME",
            os.environ.get("VPN_ROFI_THEME", str(home() / ".config" / "rofi" / "launchers" / "type-2" / "style-1.rasi")),
        )
    ).expanduser()


@dataclass
class Command:
    action: str
    dry_run: bool = False
    theme: Path = field(default_factory=_default_theme)
    flags: FlagOptions = field(default_factory=FlagOptions)
    target: str | None = None
    paths: list[str] | None = None
    mode: str = "skip"


def _option_parent() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--dry-run",
        action="store_true",
        default=argparse.SUPPRESS,
        help="print nmcli actions without changing connections",
    )
    parent.add_argument(
        "--theme",
        type=Path,
        default=argparse.SUPPRESS,
        help="Rofi theme path for picker prompts",
    )
    parent.add_argument(
        "--flag-dir",
        type=Path,
        default=argparse.SUPPRESS,
        help="directory containing local country flag images, such as us.png",
    )
    parent.add_argument(
        "--flag-cache-dir",
        type=Path,
        default=argparse.SUPPRESS,
        help="directory used for downloaded country flag images",
    )
    parent.add_argument(
        "--flag-url-base",
        default=argparse.SUPPRESS,
        help="base URL for country flag images; use an empty value to disable remote lookup",
    )
    parent.add_argument(
        "--no-emoji-flags",
        action="store_false",
        dest="emoji_flags",
        default=argparse.SUPPRESS,
        help="use generic VPN icons instead of emoji flags while image flags are missing",
    )
    parent.add_argument(
        "--no-flag-download",
        action="store_false",
        dest="flag_download",
        default=argparse.SUPPRESS,
        help="do not start background downloads for missing flag images",
    )
    return parent


def _main_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rofi-vpn",
        description="WireGuard Connection Manager for NetworkManager.",
        epilog=dedent(
            """\
            Subcommands:
              import <PATH...>       Import one or more .conf files or directories.
              remove [VPN_NAME]      Remove a VPN; omit name to pick via Rofi.

            Examples:
              rofi-vpn
              rofi-vpn US-VPN
              rofi-vpn remove US-VPN
              rofi-vpn import ~/wg/ --replace
              rofi-vpn --dry-run import ~/wg/ --fresh
            """
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[_option_parent()],
    )
    parser.add_argument("-v", "--version", action="version", version=f"rofi-vpn version {VERSION}")
    parser.add_argument(
        "command",
        nargs="?",
        metavar="SUBCOMMAND_OR_VPN",
        help="import, remove, or a VPN name to toggle directly",
    )
    parser.add_argument("args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    return parser


def _toggle_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rofi-vpn",
        description="Open the Rofi VPN picker or toggle a VPN directly.",
        parents=[_option_parent()],
    )
    parser.add_argument("target", nargs="?", help="VPN connection name to toggle")
    return parser


def _remove_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rofi-vpn remove",
        description="Remove a WireGuard connection from NetworkManager.",
        parents=[_option_parent()],
    )
    parser.add_argument("target", nargs="?", help="VPN connection name; omit to pick via Rofi")
    return parser


def _import_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rofi-vpn import",
        description="Import one or more WireGuard .conf files or directories into NetworkManager.",
        parents=[_option_parent()],
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--replace", action="store_const", const="replace", dest="mode", help="replace existing matching configs")
    mode.add_argument("--fresh", action="store_const", const="fresh", dest="mode", help="remove all existing WireGuard configs first")
    parser.set_defaults(mode="skip")
    parser.add_argument("paths", nargs="+", help="one or more .conf files or directories containing .conf files")
    return parser


def _parse(argv: list[str] | None) -> Command:
    parsed = _main_parser().parse_args(argv)
    command = parsed.command or ""
    root_dry_run = getattr(parsed, "dry_run", False)
    root_theme = Path(getattr(parsed, "theme", _default_theme())).expanduser()
    root_flags = _parse_flag_options(parsed)

    if command == "import":
        import_args = _import_parser().parse_args(parsed.args)
        return Command(
            action="import",
            dry_run=root_dry_run or getattr(import_args, "dry_run", False),
            theme=Path(getattr(import_args, "theme", root_theme)).expanduser(),
            flags=_parse_flag_options(import_args, root_flags),
            paths=import_args.paths,
            mode=import_args.mode,
        )

    if command == "remove":
        remove_args = _remove_parser().parse_args(parsed.args)
        return Command(
            action="remove",
            dry_run=root_dry_run or getattr(remove_args, "dry_run", False),
            theme=Path(getattr(remove_args, "theme", root_theme)).expanduser(),
            flags=_parse_flag_options(remove_args, root_flags),
            target=remove_args.target,
        )

    toggle_argv = ([command] if command else []) + parsed.args
    toggle_args = _toggle_parser().parse_args(toggle_argv)
    return Command(
        action="toggle",
        dry_run=root_dry_run or getattr(toggle_args, "dry_run", False),
        theme=Path(getattr(toggle_args, "theme", root_theme)).expanduser(),
        flags=_parse_flag_options(toggle_args, root_flags),
        target=toggle_args.target,
    )


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() not in {"0", "false", "no", "off"}


def _optional_env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    return Path(value).expanduser() if value else None


def _parse_flag_options(args: argparse.Namespace, base: FlagOptions | None = None) -> FlagOptions:
    defaults = base or FlagOptions(
        directory=_optional_env_path("ROFI_VPN_FLAG_DIR"),
        cache_dir=Path(os.environ.get("ROFI_VPN_FLAG_CACHE_DIR", str(home() / ".cache" / "rofi-vpn" / "flags"))).expanduser(),
        url_base=os.environ.get("ROFI_VPN_FLAG_URL_BASE", "https://flagcdn.com/w80/"),
        emoji_fallback=_env_bool("ROFI_VPN_EMOJI_FLAGS", True),
        download=_env_bool("ROFI_VPN_FLAG_DOWNLOAD", True),
    )
    return FlagOptions(
        directory=Path(getattr(args, "flag_dir", defaults.directory)).expanduser() if getattr(args, "flag_dir", defaults.directory) else None,
        cache_dir=Path(getattr(args, "flag_cache_dir", defaults.cache_dir)).expanduser(),
        url_base=getattr(args, "flag_url_base", defaults.url_base),
        emoji_fallback=getattr(args, "emoji_flags", defaults.emoji_fallback),
        download=getattr(args, "flag_download", defaults.download),
    )


def _vpn_notify(title: str, message: str, *, urgency: str = "normal", icon: str = "network-vpn") -> None:
    notify.notify(title, message, urgency=urgency, icon=icon, replace_id=NOTIF_ID, dry_run=DRY_RUN)


def _notify_load(message: str) -> None:
    _vpn_notify("VPN Manager", message, icon="network-vpn-acquiring")


def _notify_success(message: str) -> None:
    _vpn_notify("VPN Manager", message, urgency="low", icon="security-high")


def _notify_error(message: str) -> None:
    _vpn_notify("VPN Error", message, urgency="critical", icon="dialog-error")


def _extract_country_code(name: str) -> str | None:
    if not name:
        return None
    patterns = (
        r"^([A-Z]{2})([-_]|$)",
        r"[-_]([A-Z]{2})([-_]|$)",
        r"([A-Z]{2})",
        r"^([a-z]{2})([-_]|$)",
        r"[-_]([a-z]{2})([-_]|$)",
        r"([a-z]{2})",
    )
    for pattern in patterns:
        match = re.search(pattern, name)
        if match:
            return match.group(1).upper()
    return None


def _country_code_to_flag_emoji(code: str) -> str | None:
    code = code.upper()
    if len(code) != 2 or not code.isalpha() or not code.isascii():
        return None
    first, second = (ord(char) for char in code)
    if not (65 <= first <= 90 and 65 <= second <= 90):
        return None
    return chr(0x1F1E6 + first - 65) + chr(0x1F1E6 + second - 65)


def _local_flag_file(directory: Path | None, code: str) -> Path | None:
    if not directory:
        return None
    for stem in (code.lower(), code.upper()):
        for suffix in (".png", ".svg", ".jpg", ".jpeg", ".webp"):
            candidate = directory / f"{stem}{suffix}"
            if candidate.is_file():
                return candidate
    return None


def _flag_url(url_base: str, code: str) -> str:
    return url_base.rstrip("/") + f"/{code.lower()}.png"


def _download_flag_background(state: State, code: str) -> None:
    if state.dry_run or not state.flags.download or not state.flags.url_base:
        return

    cache_file = state.flags.cache_dir / f"{code.lower()}.png"
    marker = cache_file.with_suffix(cache_file.suffix + ".downloading")
    if cache_file.is_file() or marker.is_file():
        return

    state.flags.cache_dir.mkdir(parents=True, exist_ok=True)
    marker.touch()
    temp_file = cache_file.with_suffix(cache_file.suffix + ".tmp")
    script = (
        "from pathlib import Path\n"
        "import os, sys, urllib.request\n"
        "url, temp_file, cache_file, marker = sys.argv[1:]\n"
        "try:\n"
        "    urllib.request.urlretrieve(url, temp_file)\n"
        "    os.replace(temp_file, cache_file)\n"
        "except Exception:\n"
        "    Path(temp_file).unlink(missing_ok=True)\n"
        "finally:\n"
        "    Path(marker).unlink(missing_ok=True)\n"
    )
    subprocess.Popen(
        [sys.executable, "-c", script, _flag_url(state.flags.url_base, code), str(temp_file), str(cache_file), str(marker)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _flag_icon(state: State, vpn_name: str, connected: bool) -> str:
    fallback = ICON_CONNECTED if connected else ICON_DISCONNECTED
    code = _extract_country_code(vpn_name)
    if not code:
        return fallback

    local_flag = _local_flag_file(state.flags.directory, code)
    if local_flag:
        return str(local_flag)

    cached_flag = state.flags.cache_dir / f"{code.lower()}.png"
    if cached_flag.is_file():
        return str(cached_flag)

    _download_flag_background(state, code)
    emoji = _country_code_to_flag_emoji(code) if state.flags.emoji_fallback else None
    return emoji or fallback


def _prefetch_missing_flags(state: State) -> None:
    for vpn in state.all_vpns:
        code = _extract_country_code(vpn)
        if code:
            _download_flag_background(state, code)


def _selection_key(text: str) -> str:
    clean = re.sub(r"<[^>]*>", "", text).replace("*", "").replace("󰞑", "")
    return clean.strip()


def _nm_lines(args: list[str]) -> list[str]:
    return process.command_lines(["nmcli", *args])


def _init_state(dry_run: bool, theme: Path, flags: FlagOptions) -> State:
    process.require("nmcli")
    active = ""
    for line in _nm_lines(["-t", "-f", "NAME,TYPE", "connection", "show", "--active"]):
        name, _, kind = line.partition(":")
        if kind == "wireguard":
            active = name
            break
    all_vpns = []
    for line in _nm_lines(["-t", "-f", "NAME,TYPE", "connection", "show"]):
        name, _, kind = line.partition(":")
        if kind == "wireguard":
            all_vpns.append(name)
    return State(active, sorted(all_vpns), dry_run, theme, flags)


def _require_valid(state: State, name: str) -> None:
    if name not in state.all_vpns:
        raise ToolError(f"VPN '{name}' not found")


def _pick_vpn(state: State, prompt: str, message: str, exclude: str | None = None) -> str | None:
    _prefetch_missing_flags(state)
    rows = []
    choices = {}
    if state.active and state.active != exclude:
        label = f"{state.active} {VPN_CONNECTED_MARKUP}"
        rows.append(rofi.entry(label, _flag_icon(state, state.active, True)))
        choices[_selection_key(label)] = state.active
    for vpn in state.all_vpns:
        if vpn == state.active or vpn == exclude:
            continue
        rows.append(rofi.entry(vpn, _flag_icon(state, vpn, False)))
        choices[_selection_key(vpn)] = vpn
    selected = rofi.dmenu(
        rows,
        prompt=prompt,
        mesg=message,
        theme=state.theme,
        markup_rows=True,
    )
    if not selected:
        return None
    return choices.get(_selection_key(selected))


def _disconnect_active(state: State) -> None:
    if not state.active:
        return
    _notify_load(f"Disconnecting '{state.active}'...")
    process.run(["nmcli", "connection", "down", state.active], dry_run=state.dry_run)
    state.active = ""


def _cmd_toggle(state: State, target: str | None) -> int:
    if target:
        _require_valid(state, target)
    else:
        status = f"Status: Connected to {state.active}" if state.active else "Status: Unsecured"
        target = _pick_vpn(state, "VPN ", status)
        if not target:
            return 0

    if state.active and target == state.active:
        _notify_load("Disconnecting...")
        completed = process.run(["nmcli", "connection", "down", target], dry_run=state.dry_run)
        if completed.returncode == 0:
            _vpn_notify("VPN Manager", "VPN Disconnected", urgency="low", icon="network-vpn-no-route")
        else:
            _notify_error("Failed to disconnect.")
        return completed.returncode

    _notify_load("Securing Connection...")
    if state.active:
        process.run(["nmcli", "connection", "down", state.active], dry_run=state.dry_run)
    completed = process.run(["nmcli", "connection", "up", target], capture=True, dry_run=state.dry_run)
    if completed.returncode == 0 or _init_state(state.dry_run, state.theme, state.flags).active == target:
        _notify_success(f"Connected to {target}")
        return 0
    _notify_error(f"Connection Failed: {completed.stderr.strip()}")
    return completed.returncode


def _cmd_remove(state: State, target: str | None) -> int:
    if target:
        _require_valid(state, target)
    else:
        target = _pick_vpn(state, "Remove VPN ", "Select a VPN to remove")
        if not target:
            return 0
    if target == state.active:
        _disconnect_active(state)
    _notify_load(f"Removing '{target}'...")
    completed = process.run(["nmcli", "connection", "delete", target], capture=True, dry_run=state.dry_run)
    if completed.returncode == 0:
        _notify_success(f"Removed: {target}")
    else:
        _notify_error(f"Failed to remove '{target}': {completed.stderr.strip()}")
    return completed.returncode


def _derive_alias(path: Path) -> str:
    name = path.name.removesuffix(".conf")
    if IMPORT_STRIP_PREFIX and name.startswith(IMPORT_STRIP_PREFIX):
        name = name[len(IMPORT_STRIP_PREFIX) :]
    return name


def _nm_connection_exists(name: str) -> bool:
    return name in [line.partition(":")[0] for line in _nm_lines(["-t", "-f", "NAME", "connection", "show"])]


def _collect_configs(paths: list[str]) -> list[Path]:
    configs: list[Path] = []
    for value in paths:
        path = Path(value).expanduser()
        if path.is_file():
            if path.suffix == ".conf":
                configs.append(path)
            else:
                print(f"WARN: '{path}' is not a .conf file, skipping.", file=sys.stderr)
        elif path.is_dir():
            configs.extend(sorted(path.glob("*.conf")))
        else:
            print(f"WARN: '{path}' not found, skipping.", file=sys.stderr)
    return configs


def _import_one(state: State, file: Path, mode: str) -> tuple[str, bool]:
    alias = _derive_alias(file)
    if _nm_connection_exists(alias):
        if mode == "skip":
            return f"  SKIP     {alias}  (already exists)", True
        if alias == state.active:
            _disconnect_active(state)
        process.run(["nmcli", "connection", "delete", alias], dry_run=state.dry_run)

    completed = process.run(
        ["nmcli", "connection", "import", "type", "wireguard", "file", str(file)],
        capture=True,
        dry_run=state.dry_run,
    )
    if completed.returncode != 0:
        return f"  ERROR    {alias}  <- {file.name}: {completed.stderr.strip()}", False

    raw_name = alias
    match = re.search(r"Connection '([^']+)'", completed.stdout)
    if match:
        raw_name = match.group(1)
    process.run(["nmcli", "connection", "down", raw_name], dry_run=state.dry_run)
    process.run(
        ["nmcli", "connection", "modify", raw_name, "connection.id", alias, "connection.autoconnect", "no"],
        dry_run=state.dry_run,
    )
    return f"  IMPORTED {alias}  <- {file.name}", True


def _cmd_import(state: State, paths: list[str], mode: str) -> int:
    configs = _collect_configs(paths)
    if not configs:
        _notify_error("No .conf files found in the given paths.")
        return 1

    if mode == "fresh":
        _disconnect_active(state)
        if state.all_vpns:
            _notify_load("Purging all existing WireGuard configs...")
            for vpn in state.all_vpns:
                process.run(["nmcli", "connection", "delete", vpn], dry_run=state.dry_run)
                print(f"  PURGED   {vpn}")
        mode = "skip"

    _notify_load(f"Importing {len(configs)} config(s)...")
    print(f"Importing {len(configs)} config(s) [mode: {mode}]:")
    imported = skipped = errors = 0
    for file in configs:
        line, ok = _import_one(state, file, mode)
        print(line)
        if "SKIP" in line:
            skipped += 1
        elif "IMPORTED" in line:
            imported += 1
        elif not ok:
            errors += 1

    summary = f"Imported: {imported}  Skipped: {skipped}  Errors: {errors}"
    print(summary)
    if errors:
        _notify_error(f"Import finished with errors. {summary}")
        return 1
    _notify_success(summary)
    return 0


def main(argv: list[str] | None = None) -> int:
    command = _parse(argv)
    global DRY_RUN
    DRY_RUN = command.dry_run
    state = _init_state(command.dry_run, command.theme, command.flags)

    if command.action == "import":
        return _cmd_import(state, command.paths or [], command.mode)
    if command.action == "remove":
        if not state.all_vpns:
            _notify_error("No WireGuard configurations found.")
            return 1
        return _cmd_remove(state, command.target)
    if not state.all_vpns:
        _notify_error("No WireGuard configurations found.")
        return 1
    return _cmd_toggle(state, command.target)
