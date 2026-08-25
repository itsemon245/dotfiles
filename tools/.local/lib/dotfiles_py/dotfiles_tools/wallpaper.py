"""Wallpaper and theme orchestration for wally."""

from __future__ import annotations

import argparse
import os
import random
import shutil
import zlib
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

from . import notify, process, rofi
from .cli import ToolError
from .paths import cache_dir, home, xdg_cache_home


NOTIF_ID = 991011


@dataclass
class Options:
    upscale: bool = False
    no_upscale: bool = False
    dry_run: bool = False
    image: str | None = None
    wallpaper_dir: Path = Path("~/Wallpapers").expanduser()
    default_wallpaper: Path = Path("~/Wallpapers/default.png").expanduser()
    rofi_theme: Path = Path("~/.config/rofi/launchers/type-3/style-2-big-thumb.rasi").expanduser()
    openrgb_script: Path = Path("~/.config/OpenRGB/scripts/wallust-colors.sh").expanduser()
    backend: str = "auto"
    target_width: int = 2560
    transition_type: str = "random"
    transition_fps: str = "60"
    transition_duration: str = "2"
    transition_pos: str = "0.5,0.5"
    wallust: bool = True
    openrgb: bool = True
    upscaler_bin: str = "realesrgan-ncnn-vulkan"
    upscale_model: str = "realesrgan-x4plus-anime"


def _env_path(name: str, default: Path) -> Path:
    return Path(os.environ.get(name, str(default))).expanduser()


def _env_first_path(names: tuple[str, ...], default: Path) -> Path:
    for name in names:
        value = os.environ.get(name)
        if value:
            return Path(value).expanduser()
    return default.expanduser()


def _env_first(names: tuple[str, ...], default: str) -> str:
    for name in names:
        value = os.environ.get(name)
        if value is not None:
            return value
    return default


def _env_bool(names: tuple[str, ...], default: bool) -> bool:
    value = _env_first(names, "true" if default else "false").lower()
    return value not in {"0", "false", "no", "off"}


def _positive_int(value: int | str, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ToolError(f"{name} must be an integer") from exc
    if parsed <= 0:
        raise ToolError(f"{name} must be greater than zero")
    return parsed


def _option_parent() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "-u",
        "--upscale",
        action="store_true",
        default=argparse.SUPPRESS,
        help="enable AI upscaling if not already cached",
    )
    parent.add_argument(
        "--no-upscale",
        action="store_true",
        default=argparse.SUPPRESS,
        help="force the original image and ignore upscale cache",
    )
    parent.add_argument(
        "--dry-run",
        action="store_true",
        default=argparse.SUPPRESS,
        help="print intended actions without changing system state",
    )
    parent.add_argument(
        "--wallpaper-dir",
        type=Path,
        default=argparse.SUPPRESS,
        help="wallpaper search directory for picker mode and relative set paths",
    )
    parent.add_argument(
        "--default-wallpaper",
        type=Path,
        default=argparse.SUPPRESS,
        help="target image path written before applying wallpaper/theme",
    )
    parent.add_argument(
        "--theme",
        dest="rofi_theme",
        type=Path,
        default=argparse.SUPPRESS,
        help="Rofi theme path for picker mode",
    )
    parent.add_argument(
        "--backend",
        choices=["auto", "awww", "swww", "none"],
        default=argparse.SUPPRESS,
        help="wallpaper backend to use",
    )
    parent.add_argument(
        "--target-width",
        type=int,
        default=argparse.SUPPRESS,
        help="max width for optimized upscaled wallpapers",
    )
    parent.add_argument(
        "--transition-type",
        default=argparse.SUPPRESS,
        help="wallpaper transition type, or random",
    )
    parent.add_argument(
        "--transition-fps",
        default=argparse.SUPPRESS,
        help="wallpaper transition FPS",
    )
    parent.add_argument(
        "--transition-duration",
        default=argparse.SUPPRESS,
        help="wallpaper transition duration",
    )
    parent.add_argument(
        "--transition-pos",
        default=argparse.SUPPRESS,
        help="wallpaper transition position, for example 0.5,0.5",
    )
    parent.add_argument(
        "--openrgb-script",
        type=Path,
        default=argparse.SUPPRESS,
        help="OpenRGB theme sync script path",
    )
    parent.add_argument(
        "--no-wallust",
        action="store_false",
        dest="wallust",
        default=argparse.SUPPRESS,
        help="skip Wallust color generation and desktop reload",
    )
    parent.add_argument(
        "--no-openrgb",
        action="store_false",
        dest="openrgb",
        default=argparse.SUPPRESS,
        help="skip OpenRGB theme sync",
    )
    parent.add_argument(
        "--upscaler-bin",
        default=argparse.SUPPRESS,
        help="AI upscaler executable",
    )
    parent.add_argument(
        "--upscale-model",
        default=argparse.SUPPRESS,
        help="AI upscaler model name",
    )
    return parent


def _parser() -> argparse.ArgumentParser:
    options = _option_parent()
    parser = argparse.ArgumentParser(
        prog="wally",
        description="Set wallpapers, generate Wallust themes, and reload desktop colors.",
        epilog=dedent(
            """\
            Omit the command to open the Rofi wallpaper picker.

            Examples:
              wally
              wally set ~/Wallpapers/image.png
              wally -u set image.jpg
              wally set image.jpg --no-upscale
              wally --wallpaper-dir ~/Pictures/walls --theme ~/.config/rofi/theme.rasi
              wally --backend swww --transition-type fade set image.png
            """
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[options],
    )
    subparsers = parser.add_subparsers(dest="command", metavar="[command]")
    set_parser = subparsers.add_parser(
        "set",
        parents=[options],
        help="set a specific image path or a file from ~/Wallpapers",
        description="Set a specific image path or a file from ~/Wallpapers.",
    )
    set_parser.add_argument("image", help="image path or filename under ~/Wallpapers")
    return parser


def _parse(argv: list[str] | None) -> Options:
    args = _parser().parse_args(argv)
    wallpaper_dir = Path(getattr(args, "wallpaper_dir", _env_path("WALLPAPER_DIR", home() / "Wallpapers"))).expanduser()
    default_wallpaper = Path(
        getattr(args, "default_wallpaper", _env_path("DEFAULT_WALLPAPER", wallpaper_dir / "default.png"))
    ).expanduser()
    backend = str(getattr(args, "backend", _env_first(("WALLY_BACKEND", "WALLPAPER_BACKEND"), "auto"))).lower()
    if backend not in {"auto", "awww", "swww", "none"}:
        raise ToolError(f"backend must be one of: auto, awww, swww, none (got {backend})")
    return Options(
        upscale=getattr(args, "upscale", False),
        no_upscale=getattr(args, "no_upscale", False),
        dry_run=getattr(args, "dry_run", False),
        image=getattr(args, "image", None),
        wallpaper_dir=wallpaper_dir,
        default_wallpaper=default_wallpaper,
        rofi_theme=Path(
            getattr(
                args,
                "rofi_theme",
                _env_first_path(
                    ("WALLY_ROFI_THEME", "ROFI_THEME"),
                    home() / ".config" / "rofi" / "launchers" / "type-3" / "style-2-big-thumb.rasi",
                ),
            )
        ).expanduser(),
        openrgb_script=Path(
            getattr(args, "openrgb_script", _env_path("OPENRGB_SCRIPT", home() / ".config/OpenRGB/scripts/wallust-colors.sh"))
        ).expanduser(),
        backend=backend,
        target_width=_positive_int(getattr(args, "target_width", _env_first(("TARGET_WIDTH", "WALLY_TARGET_WIDTH"), "2560")), "target width"),
        transition_type=getattr(args, "transition_type", _env_first(("TRANSITION_TYPE", "WALLY_TRANSITION_TYPE"), "random")),
        transition_fps=getattr(args, "transition_fps", _env_first(("TRANSITION_FPS", "WALLY_TRANSITION_FPS"), "60")),
        transition_duration=getattr(args, "transition_duration", _env_first(("TRANSITION_DURATION", "WALLY_TRANSITION_DURATION"), "2")),
        transition_pos=getattr(args, "transition_pos", _env_first(("TRANSITION_POS", "WALLY_TRANSITION_POS"), "0.5,0.5")),
        wallust=getattr(args, "wallust", _env_bool(("WALLY_WALLUST",), True)),
        openrgb=getattr(args, "openrgb", _env_bool(("WALLY_OPENRGB",), True)),
        upscaler_bin=getattr(args, "upscaler_bin", _env_first(("UPSCALER_BIN", "WALLY_UPSCALER_BIN"), "realesrgan-ncnn-vulkan")),
        upscale_model=getattr(args, "upscale_model", _env_first(("UPSCALE_MODEL", "WALLY_UPSCALE_MODEL"), "realesrgan-x4plus-anime")),
    )


def _wally_notify(message: str, *, urgency: str = "normal", icon: str = "image-x-generic", dry_run: bool = False) -> None:
    notify.notify("Wally", message, urgency=urgency, icon=icon, replace_id=NOTIF_ID, dry_run=dry_run)


def _wally_progress(percent: int, message: str, *, icon: str = "image-x-generic", dry_run: bool = False) -> None:
    notify.progress("Wally", message, percent, icon=icon, replace_id=NOTIF_ID, dry_run=dry_run)


def _images(opts: Options) -> list[Path]:
    directory = opts.wallpaper_dir
    suffixes = {".jpg", ".jpeg", ".png", ".webp"}
    if not directory.is_dir():
        return []
    default_wallpaper = opts.default_wallpaper.resolve(strict=False)
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in suffixes and path.resolve(strict=False) != default_wallpaper
    )


def _pick_wallpaper(opts: Options) -> Path | None:
    images = _images(opts)
    if not images:
        raise ToolError(f"no images found in {opts.wallpaper_dir}")
    rows = [rofi.entry("Random", "media-playlist-shuffle")]
    rows.extend(rofi.entry(path.name, str(path)) for path in images)
    selected = rofi.dmenu(
        rows,
        prompt="Wallpaper",
        theme=opts.rofi_theme,
    )
    if not selected:
        return None
    if selected == "Random":
        return random.choice(images)
    candidate = opts.wallpaper_dir / selected
    if not candidate.is_file():
        raise ToolError(f"image not found: {selected}")
    return candidate


def _resolve_direct_input(input_path: str, opts: Options) -> Path:
    path = Path(input_path).expanduser()
    if path.is_file():
        return path
    path = opts.wallpaper_dir / input_path
    if path.is_file():
        return path
    raise ToolError(f"image not found: {input_path}")


def _cache_stem(path: Path) -> str:
    checksum = zlib.crc32(str(path).encode("utf-8")) & 0xFFFFFFFF
    return f"{path.stem}_{checksum}"


def _convert_command() -> str:
    if process.command_exists("magick"):
        return "magick"
    if process.command_exists("convert"):
        return "convert"
    raise ToolError("missing required command: magick or convert")


def _wally_cache(opts: Options) -> Path:
    if opts.dry_run:
        return xdg_cache_home() / "wally"
    return cache_dir("wally")


def _normalize_wallpaper(path: Path, opts: Options) -> tuple[Path, str]:
    default = opts.default_wallpaper
    cache = _wally_cache(opts)
    stem = _cache_stem(path)
    if opts.dry_run:
        print(f"+ mkdir -p {default.parent}")
    else:
        default.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".png":
        if opts.dry_run:
            print(f"+ copy {path} {default}")
        else:
            shutil.copy2(path, default)
        return path, stem

    normalized = cache / f"{stem}.png"
    _wally_progress(20, "Normalizing to PNG...", icon=str(path), dry_run=opts.dry_run)
    if opts.dry_run:
        print(f"+ {_convert_command() if process.command_exists('magick') or process.command_exists('convert') else 'magick'} {path} {normalized}")
        print(f"+ copy {normalized} {default}")
    else:
        process.run([_convert_command(), str(path), str(normalized)], check=True)
        shutil.copy2(normalized, default)
    return normalized, stem


def _transition_flags(opts: Options) -> list[str]:
    transition_type = opts.transition_type
    if transition_type == "random":
        transition_type = random.choice(["simple", "fade", "left", "right", "top", "bottom", "wipe", "wave", "grow", "center", "outer"])
    return [
        "--transition-type",
        transition_type,
        "--transition-fps",
        opts.transition_fps,
        "--transition-duration",
        opts.transition_duration,
        "--transition-pos",
        opts.transition_pos,
    ]


def _reload_desktop(*, dry_run: bool) -> None:
    if process.pgrep("-x", "waybar"):
        process.pkill("-x", "waybar", dry_run=dry_run)
        if process.command_exists("waybar"):
            process.background(["waybar"], dry_run=dry_run)
    process.pkill("-x", "dunst", dry_run=dry_run)
    process.pkill("-USR1", "-x", "kitty", dry_run=dry_run)
    process.pkill("-USR1", "-x", "qt5ct", dry_run=dry_run)

    if process.command_exists("gsettings"):
        current = process.output(["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"]).strip().strip("'")
        if current:
            process.run(["gsettings", "set", "org.gnome.desktop.interface", "gtk-theme", "Default"], dry_run=dry_run)
            process.run(["gsettings", "set", "org.gnome.desktop.interface", "gtk-theme", current], dry_run=dry_run)


def _update_system_theme(image: Path, opts: Options) -> None:
    if not opts.wallust:
        _wally_notify("Wallust disabled; skipped color generation.", dry_run=opts.dry_run)
        return
    if process.command_exists("wallust"):
        _wally_progress(70, "Generating colors...", icon=str(image), dry_run=opts.dry_run)
        completed = process.run(["wallust", "run", str(image), "-q"], dry_run=opts.dry_run)
        if completed.returncode != 0:
            _wally_notify("Wallust failed; wallpaper was still applied.", urgency="critical", dry_run=opts.dry_run)
        elif process.command_exists("hyprctl"):
            process.run(["hyprctl", "reload"], dry_run=opts.dry_run)
        _reload_desktop(dry_run=opts.dry_run)
    else:
        _wally_notify("Wallust is not installed; skipped color generation.", dry_run=opts.dry_run)


def _sync_openrgb(opts: Options) -> None:
    if not opts.openrgb:
        return
    script = opts.openrgb_script
    if script.is_file() and process.command_exists("openrgb"):
        completed = process.run(["bash", str(script)], dry_run=opts.dry_run)
        if completed.returncode != 0:
            _wally_notify("OpenRGB theme sync failed.", dry_run=opts.dry_run)


def _resolve_backend(opts: Options) -> str | None:
    if opts.backend == "none":
        return None
    if opts.backend != "auto":
        if process.command_exists(opts.backend) or opts.dry_run:
            return opts.backend
        raise ToolError(f"configured wallpaper backend is not installed: {opts.backend}")
    return "awww" if process.command_exists("awww") else "swww" if process.command_exists("swww") else None


def _apply_wallpaper(opts: Options) -> None:
    default = opts.default_wallpaper
    backend = _resolve_backend(opts)
    if backend:
        process.run([backend, "img", str(default), *_transition_flags(opts)], dry_run=opts.dry_run, check=not opts.dry_run)
    else:
        _wally_notify("No wallpaper backend found; generated theme only.", dry_run=opts.dry_run)
    _update_system_theme(default, opts)
    _sync_openrgb(opts)


def _apply_upscaled(normalized: Path, stem: str, opts: Options) -> None:
    if opts.no_upscale:
        _wally_notify("Original wallpaper set.", dry_run=opts.dry_run)
        return

    cache = _wally_cache(opts)
    cache_file = cache / f"{stem}_upscaled.png"
    temp_upscale = cache / f"{stem}.upscale.tmp.png"
    default = opts.default_wallpaper
    if cache_file.is_file():
        _wally_progress(80, "Using cached upscale...", icon=str(cache_file), dry_run=opts.dry_run)
        if opts.dry_run:
            print(f"+ copy {cache_file} {default}")
        else:
            shutil.copy2(cache_file, default)
        _apply_wallpaper(opts)
        _wally_notify("Cached wallpaper set.", dry_run=opts.dry_run)
        return

    if not opts.upscale:
        _wally_notify("Wallpaper set.", dry_run=opts.dry_run)
        return

    upscaler = opts.upscaler_bin
    if not opts.dry_run:
        process.require(upscaler)
    _wally_progress(50, "Upscaling...", icon=str(normalized), dry_run=opts.dry_run)
    process.run(
        [upscaler, "-i", str(normalized), "-o", str(temp_upscale), "-n", opts.upscale_model, "-s", "4", "-t", "400"],
        dry_run=opts.dry_run,
        check=not opts.dry_run,
    )
    _wally_progress(60, "Optimizing size...", icon=str(normalized), dry_run=opts.dry_run)
    command = _convert_command() if not opts.dry_run else "magick"
    process.run([command, str(temp_upscale), "-resize", f"{opts.target_width}x", str(cache_file)], dry_run=opts.dry_run, check=not opts.dry_run)
    if not opts.dry_run:
        temp_upscale.unlink(missing_ok=True)
        shutil.copy2(cache_file, default)
    else:
        print(f"+ remove {temp_upscale}")
        print(f"+ copy {cache_file} {default}")
    _apply_wallpaper(opts)
    _wally_notify("Wallpaper set.", dry_run=opts.dry_run)


def main(argv: list[str] | None = None) -> int:
    opts = _parse(argv)
    path = _resolve_direct_input(opts.image, opts) if opts.image else _pick_wallpaper(opts)
    if path is None:
        return 0
    if not path.is_file():
        raise ToolError(f"file not found: {path}")

    _wally_progress(10, "Initializing...", icon=str(path), dry_run=opts.dry_run)
    normalized, stem = _normalize_wallpaper(path, opts)
    _wally_progress(30, "Setting preview...", icon=str(path), dry_run=opts.dry_run)
    _apply_wallpaper(opts)
    _apply_upscaled(normalized, stem, opts)
    return 0
