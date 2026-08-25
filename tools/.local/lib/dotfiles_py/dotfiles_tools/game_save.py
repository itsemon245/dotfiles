"""Back up and restore Wine/Proton game save state."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import process
from .cli import ToolError


DEFAULT_SAVE_ROOT = Path("/mnt/HDD/Games/Saves")
DEFAULT_PREFIX_ROOT = Path("/mnt/HDD/Games/Prefixes")
DEFAULT_INSTALLED_ROOT = Path("/mnt/HDD/Games/Installed")

SAVE_PATHS = (
    Path("drive_c/users"),
    Path("drive_c/ProgramData"),
    Path("user.reg"),
    Path("userdef.reg"),
    Path("system.reg"),
)

INSTALLED_BACKUP_DIR = Path("installed")
INSTALLED_MANIFEST = Path("installed.manifest")

INSTALLED_SAVE_DIR_KEYS = {
    "profile",
    "profiles",
    "remote",
    "save",
    "saved",
    "savedata",
    "savedgames",
    "savegame",
    "savegames",
    "saves",
    "userdata",
}

INSTALLED_SAVE_FILE_SUFFIXES = {
    ".sav",
    ".save",
    ".save-backup",
    ".slot",
    ".usr-data",
}

INSTALLED_SAVE_FILE_NAMES = {
    "lastauto.dat",
    "lastbackup.dat",
    "lastcamp.dat",
    "profile.dat",
}

INSTALLED_SAVE_FILE_STEM_PREFIXES = (
    "autosave",
    "manualsave",
    "profile",
    "quicksave",
    "save",
    "slot",
)

CACHE_EXCLUDES = (
    "dxvk/",
    "INetCache/",
    "Package Cache/",
    "NVIDIA/",
    "psolibs/",
    "Logs/",
    "Crashes/",
    "CrashReportClient/",
    "DerivedDataCache/",
    "webcache/",
    "*.dxvk.bin",
    "*.dxvk.lut",
    "*.log",
    "*.mdmp",
    "*.dmp",
    "sga_*.vkPipelineCacheWindows",
)

TRANSFERRED_RE = re.compile(r"^Total transferred file size:\s+([0-9,]+)\s+bytes$", re.MULTILINE)


@dataclass(frozen=True)
class Args:
    command: str
    save_root: Path
    prefix_root: Path
    name: str
    include_cache: bool
    include_installed_saves: bool
    installed_root: Path
    installed_dir: Path | None
    verbose: bool


def parse_args() -> Args:
    parser = argparse.ArgumentParser(
        prog="game-save",
        description="Export or import save-related Wine/Proton prefix state.",
    )
    parser.add_argument("command", choices=("export", "import"))
    parser.add_argument(
        "-P",
        "--path",
        type=Path,
        default=DEFAULT_SAVE_ROOT,
        dest="save_root",
        help=f"save backup root [default: {DEFAULT_SAVE_ROOT}]",
    )
    parser.add_argument(
        "--prefix-root",
        type=Path,
        default=DEFAULT_PREFIX_ROOT,
        help=f"game prefix root [default: {DEFAULT_PREFIX_ROOT}]",
    )
    parser.add_argument(
        "--name",
        default="all",
        help='game/prefix directory name, or "all" [default: all]',
    )
    parser.add_argument(
        "--include-cache",
        action="store_true",
        help="include known runtime caches and installer caches",
    )
    parser.add_argument(
        "--installed-dir",
        nargs="?",
        default=None,
        const="",
        metavar="PATH",
        help=(
            "include installed-game save dirs; without PATH uses "
            f"{DEFAULT_INSTALLED_ROOT}/<name>"
        ),
    )
    parser.add_argument(
        "--installed-root",
        type=Path,
        default=DEFAULT_INSTALLED_ROOT,
        help=f"installed games root for --installed-dir without PATH [default: {DEFAULT_INSTALLED_ROOT}]",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="show each synced save path",
    )
    namespace = parser.parse_args()

    if not namespace.name:
        raise ToolError("--name cannot be empty")

    installed_dir = None
    if namespace.installed_dir not in (None, ""):
        installed_dir = Path(namespace.installed_dir).expanduser()
        if namespace.name == "all":
            raise ToolError("--installed-dir PATH requires --name; use --installed-root with --installed-dir for all games")

    return Args(
        command=namespace.command,
        save_root=namespace.save_root.expanduser(),
        prefix_root=namespace.prefix_root.expanduser(),
        name=namespace.name,
        include_cache=namespace.include_cache,
        include_installed_saves=namespace.installed_dir is not None,
        installed_root=namespace.installed_root.expanduser(),
        installed_dir=installed_dir,
        verbose=namespace.verbose,
    )


def validate_dependencies(args: Args) -> None:
    process.require("rsync")

    if not args.prefix_root.is_dir():
        raise ToolError(f"prefix root does not exist: {args.prefix_root}")

    if args.command == "export":
        args.save_root.mkdir(parents=True, exist_ok=True)
    elif not args.save_root.is_dir():
        raise ToolError(f"save backup root does not exist: {args.save_root}")


def selected_games(args: Args) -> list[str]:
    if args.name != "all":
        prefix = args.prefix_root / args.name
        if not prefix.is_dir():
            raise ToolError(f"prefix not found: {prefix}")
        return [args.name]

    games = sorted(path.name for path in args.prefix_root.iterdir() if path.is_dir())
    if not games:
        raise ToolError(f"no prefixes found in: {args.prefix_root}")
    return games


def validate_import(args: Args, games: list[str]) -> None:
    errors: list[str] = []
    for game in games:
        prefix = args.prefix_root / game
        save = args.save_root / game
        if not prefix.is_dir():
            errors.append(f"prefix not found: {prefix}")
        if not save.is_dir():
            errors.append(f"save backup not found: {save}")

    if errors:
        raise ToolError("\nerror: ".join(errors))


def validate_installed_dirs(args: Args, games: list[str]) -> None:
    if not args.include_installed_saves:
        return

    errors: list[str] = []
    for game in games:
        installed_dir = installed_game_dir(args, game)
        if not installed_dir.is_dir():
            errors.append(f"installed game directory not found: {installed_dir}")

    if errors:
        raise ToolError("\nerror: ".join(errors))


def human_bytes(size: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    amount = float(size)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(amount)} {unit}"
            if amount < 10:
                return f"{amount:.1f} {unit}"
            return f"{amount:.0f} {unit}"
        amount /= 1024
    return f"{size} B"


def disk_usage_bytes(path: Path) -> int:
    seen: set[tuple[int, int]] = set()

    def walk(current: Path) -> int:
        try:
            stat = current.lstat()
        except OSError:
            return 0

        key = (stat.st_dev, stat.st_ino)
        if key in seen:
            return 0
        seen.add(key)

        total = getattr(stat, "st_blocks", 0) * 512
        if total == 0:
            total = stat.st_size

        if not current.is_dir() or current.is_symlink():
            return total

        try:
            entries = list(current.iterdir())
        except OSError:
            return total

        return total + sum(walk(entry) for entry in entries)

    return walk(path) if path.exists() else 0


def transferred_bytes(output: str) -> int:
    match = TRANSFERRED_RE.search(output)
    if not match:
        return 0
    return int(match.group(1).replace(",", ""))


def rsync_exclude_args(include_cache: bool) -> list[str]:
    if include_cache:
        return []

    args: list[str] = []
    for pattern in CACHE_EXCLUDES:
        args.extend(["--exclude", pattern])
    return args


def installed_game_dir(args: Args, game: str) -> Path:
    if args.installed_dir is not None:
        return args.installed_dir
    return args.installed_root / game


def normalized_key(value: str) -> str:
    return re.sub(r"[\s_.-]+", "", value.casefold())


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def is_installed_save_dir(path: Path) -> bool:
    return normalized_key(path.name) in INSTALLED_SAVE_DIR_KEYS


def is_installed_save_file(path: Path) -> bool:
    name = path.name.casefold()
    stem = normalized_key(path.stem)

    if name in INSTALLED_SAVE_FILE_NAMES:
        return True
    if any(name.endswith(suffix) for suffix in INSTALLED_SAVE_FILE_SUFFIXES):
        return True
    if path.suffix.casefold() == ".dat" and stem.startswith(INSTALLED_SAVE_FILE_STEM_PREFIXES):
        return True
    return False


def topmost_paths(paths: list[Path]) -> list[Path]:
    selected: list[Path] = []
    for path in sorted(paths, key=lambda item: (len(item.parts), item.as_posix())):
        if any(is_relative_to(path, parent) for parent in selected):
            continue
        selected.append(path)
    return selected


def installed_save_entries(installed_dir: Path) -> list[tuple[str, Path]]:
    dirs: list[Path] = []
    files: list[Path] = []

    for path in installed_dir.rglob("*"):
        relative = path.relative_to(installed_dir)
        if path.is_dir():
            if is_installed_save_dir(path):
                dirs.append(relative)
        elif path.is_file() and is_installed_save_file(path):
            files.append(relative)

    selected_dirs = topmost_paths(dirs)
    selected_files = [
        path
        for path in sorted(files, key=lambda item: item.as_posix())
        if not any(is_relative_to(path, directory) for directory in selected_dirs)
    ]

    return [("dir", path) for path in selected_dirs] + [("file", path) for path in selected_files]


def validate_manifest_path(path: Path) -> None:
    if path.is_absolute() or ".." in path.parts:
        raise ToolError(f"invalid installed save manifest path: {path}")


def write_installed_manifest(save: Path, entries: list[tuple[str, Path]]) -> None:
    manifest = save / INSTALLED_MANIFEST
    lines = []
    for kind, relative in entries:
        validate_manifest_path(relative)
        lines.append(f"{kind}\t{relative.as_posix()}\n")
    manifest.write_text("".join(lines), encoding="utf-8")


def read_installed_manifest(save: Path) -> list[tuple[str, Path]]:
    manifest = save / INSTALLED_MANIFEST
    if not manifest.is_file():
        return []

    entries: list[tuple[str, Path]] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            kind, raw_path = line.split("\t", 1)
        except ValueError as exc:
            raise ToolError(f"invalid installed save manifest line: {line}") from exc
        if kind not in {"dir", "file"}:
            raise ToolError(f"invalid installed save manifest kind: {kind}")
        relative = Path(raw_path)
        validate_manifest_path(relative)
        entries.append((kind, relative))
    return entries


def run_rsync(
    source: Path,
    destination: Path,
    *,
    is_dir: bool,
    include_cache: bool,
    delete_excluded: bool,
) -> int:
    command = ["rsync", "-aHAX", "--stats"]
    if is_dir:
        command.append("--delete")
        if delete_excluded and not include_cache:
            command.append("--delete-excluded")
        command.extend(rsync_exclude_args(include_cache))
        destination.mkdir(parents=True, exist_ok=True)
        command.extend([str(source) + "/", str(destination) + "/"])
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        command.extend([str(source), str(destination)])

    env = os.environ.copy()
    env["LC_ALL"] = "C"
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        check=False,
    )
    if completed.returncode != 0:
        if completed.stdout:
            print(completed.stdout, end="")
        raise ToolError(f"rsync failed: {process.printable(command)}")

    return transferred_bytes(completed.stdout)


def clear_installed_backup(save: Path) -> None:
    installed_backup = save / INSTALLED_BACKUP_DIR
    manifest = save / INSTALLED_MANIFEST
    if installed_backup.exists():
        shutil.rmtree(installed_backup)
    manifest.unlink(missing_ok=True)


def sync_installed_saves(args: Args, game: str, *, is_export: bool) -> int:
    installed_dir = installed_game_dir(args, game)
    save = args.save_root / game
    installed_backup = save / INSTALLED_BACKUP_DIR
    transferred = 0

    if is_export:
        entries = installed_save_entries(installed_dir)
        if not entries:
            clear_installed_backup(save)
            if args.verbose:
                print(f"installed skip {installed_dir}")
            return 0

        installed_backup.mkdir(parents=True, exist_ok=True)
        write_installed_manifest(save, entries)
        source_root = installed_dir
        destination_root = installed_backup
    else:
        entries = read_installed_manifest(save)
        if not entries:
            if args.verbose:
                print(f"installed skip {installed_backup}")
            return 0

        source_root = installed_backup
        destination_root = installed_dir

    for kind, relative in entries:
        source = source_root / relative
        destination = destination_root / relative
        is_dir = kind == "dir"

        if is_dir and not source.is_dir():
            raise ToolError(f"installed save directory not found: {source}")
        if not is_dir and not source.is_file():
            raise ToolError(f"installed save file not found: {source}")

        copied = run_rsync(
            source,
            destination,
            is_dir=is_dir,
            include_cache=args.include_cache,
            delete_excluded=is_export,
        )
        transferred += copied
        if args.verbose:
            label = "installed dir" if is_dir else "installed file"
            print(f"{label} {relative} ({human_bytes(copied)} transferred)")

    return transferred


def sync_game(args: Args, game: str) -> int:
    is_export = args.command == "export"
    prefix = args.prefix_root / game
    save = args.save_root / game
    source_root = prefix if is_export else save
    destination_root = save if is_export else prefix
    label = "Export" if is_export else "Import"
    transferred = 0

    print()
    print(f"== {label}: {game} ==")
    destination_root.mkdir(parents=True, exist_ok=True)

    for relative in SAVE_PATHS:
        source = source_root / relative
        destination = destination_root / relative
        display = str(relative)

        if source.is_dir():
            copied = run_rsync(
                source,
                destination,
                is_dir=True,
                include_cache=args.include_cache,
                delete_excluded=is_export,
            )
            transferred += copied
            if args.verbose:
                print(f"dir  {display} ({human_bytes(copied)} transferred)")
        elif source.is_file():
            copied = run_rsync(
                source,
                destination,
                is_dir=False,
                include_cache=args.include_cache,
                delete_excluded=False,
            )
            transferred += copied
            if args.verbose:
                print(f"file {display} ({human_bytes(copied)} transferred)")
        else:
            if args.verbose:
                print(f"skip {display}")

    if args.include_installed_saves:
        transferred += sync_installed_saves(args, game, is_export=is_export)

    save_size = disk_usage_bytes(save)
    print(f"transferred this run: {human_bytes(transferred)}")
    print(f"size: {human_bytes(save_size)}")
    return transferred


def main() -> int:
    args = parse_args()
    validate_dependencies(args)
    games = selected_games(args)
    validate_installed_dirs(args, games)

    if args.command == "import":
        validate_import(args, games)

    total_transferred = 0
    for game in games:
        total_transferred += sync_game(args, game)

    if args.name == "all":
        print()
        print(f"Total transferred this run: {human_bytes(total_transferred)}")
        print(f"Total size: {human_bytes(disk_usage_bytes(args.save_root))}")
    print("Done.")
    return 0
