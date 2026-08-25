"""Optimize visual novel assets for Android/JoiPlay sized libraries."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from . import process
from .cli import ToolError


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
AUDIO_EXTS = {".ogg", ".mp3", ".wav"}
VIDEO_EXTS = {".mp4", ".m4v", ".mov", ".webm"}
OPTIMIZABLE_EXTS = IMAGE_EXTS | AUDIO_EXTS | VIDEO_EXTS
MANIFEST_NAME = ".vn-optimize-assets.json"
MANIFEST_VERSION = 2
WORK_BASE_NAME = ".vn-optimize-assets-work"
WORK_MANIFEST_NAME = ".vn-optimize-assets-work.json"
WORK_PAYLOAD_NAME = "payload"
WORK_FILE_FULL_HASH_LIMIT = 16 * 1024 * 1024
EXTRACTION_PROGRESS_INTERVAL = 5.0
PROGRESS_PRINT_INTERVAL = 1.0
DEFAULT_ARCHIVE_FORMAT = "7z"
DEFAULT_ZSTD_LEVEL = 19
AUTO_FULL_HASH_LIMIT = 2 * 1024 * 1024 * 1024
PARTIAL_HASH_BYTES = 16 * 1024 * 1024
LOW_VALUE_MEDIA_RATIO = 0.05
LOW_VALUE_PACKED_BYTES = 100 * 1024 * 1024
LOW_VALUE_PACKED_MULTIPLIER = 10
PACKED_EXTS = {
    ".apk",
    ".rpa",
    ".xp3",
    ".zip",
    ".7z",
    ".rar",
    ".tar",
    ".tgz",
    ".gz",
    ".xz",
    ".zst",
    ".bz2",
}
ARCHIVE_SUFFIXES = (
    ".tar.zst",
    ".tar.xz",
    ".tar.bz2",
    ".tar.gz",
    ".tbz2",
    ".tgz",
    ".txz",
    ".zip",
    ".7z",
    ".rar",
    ".tar",
)
UNSUPPORTED_SOURCE_ARCHIVE_SUFFIXES = (".apk", ".rpa", ".xp3")
UNITY_PACKED_EXTS = {
    ".assets",
    ".bundle",
    ".bank",
    ".data",
    ".dat",
    ".resource",
    ".ress",
    ".resS".lower(),
    ".unity3d",
}
RPGM_ENCRYPTED_EXTS = {".rpgmvp", ".rpgmvo", ".rpgmvm"}
RPGM_SPRITE_DIRS = {
    "animations",
    "battlebacks1",
    "battlebacks2",
    "characters",
    "enemies",
    "faces",
    "system",
    "sv_actors",
    "sv_enemies",
    "tilesets",
    "weather",
}
RPGM_SAFE_IMAGE_DIRS = {"pictures", "parallaxes", "titles1", "titles2"}
HTML_SKIP_DIRS = {
    ".cache",
    ".git",
    "cache",
    "node_modules",
    "serviceworker",
    "service-worker",
    "temp",
    "tmp",
}
HTML_INTEGRITY_MARKERS = {
    "asset-manifest.json",
    "precache-manifest.js",
    "service-worker.js",
    "sw.js",
}
UNITY_SKIP_DIR_NAMES = {
    "assetbundles",
    "managed",
    "plugins",
    "streamingassets",
}


@dataclass(frozen=True)
class Profile:
    max_size: str
    jpeg_quality: int
    webp_quality: int
    ogg_quality: int
    mp3_bitrate: str
    video_crf: int
    webm_crf: int


PROFILES = {
    "phone-fhd": Profile("1920x1080", 90, 88, 4, "128k", 24, 34),
    "phone-fhd-hq": Profile("1920x1080", 92, 90, 5, "160k", 22, 32),
    "small": Profile("1600x900", 85, 82, 3, "96k", 27, 37),
}


@dataclass(frozen=True)
class Settings:
    command: str
    source: Path
    dst: Path | None
    apply: bool
    in_place: bool
    force: bool
    extract: str
    pipeline: bool
    work_dir: Path | None
    keep_work_dir: bool
    clean_work_dir: bool
    resume: bool
    progress: str
    low_value: str
    jobs: int
    video_jobs: int
    extract_jobs: int
    stable_seconds: float
    engine_policy: str
    manifest: bool
    hash_mode: str
    max_size: str
    jpeg_quality: int
    webp_quality: int
    ogg_quality: int
    mp3_bitrate: str
    video_crf: int
    webm_crf: int
    video_encoder: str
    video_preset: str
    nvenc_preset: str
    ffmpeg_threads: int
    magick_threads: int
    skip_images: bool
    skip_audio: bool
    skip_video: bool
    strip_pc_runtime: bool
    strip_cache: bool
    archive_format: str
    output_archive: Path | None
    zstd_level: int
    zstd_long: int | None
    sevenzip_level: int
    verbose: bool


@dataclass(frozen=True)
class FileResult:
    path: Path
    status: str
    before: int
    after: int
    message: str | None = None

    @property
    def saved(self) -> int:
        return max(0, self.before - self.after)


@dataclass(frozen=True)
class OptimizationTask:
    path: Path
    before_identity: dict[str, object]


@dataclass
class Stats:
    lock: threading.Lock = field(default_factory=threading.Lock)
    candidates: int = 0
    candidate_bytes: int = 0
    packed: int = 0
    packed_bytes: int = 0
    packed_exts: dict[str, int] = field(default_factory=dict)
    optimized: int = 0
    skipped: int = 0
    failed: int = 0
    unsafe_skipped: int = 0
    unsafe_reasons: dict[str, int] = field(default_factory=dict)
    before_bytes: int = 0
    after_bytes: int = 0
    removed: int = 0
    removed_bytes: int = 0
    processed: int = 0
    processed_bytes: int = 0
    processed_after_bytes: int = 0
    processed_optimized: int = 0
    processed_skipped: int = 0
    processed_failed: int = 0
    resumed: int = 0

    def add_candidate(self, size: int) -> None:
        with self.lock:
            self.candidates += 1
            self.candidate_bytes += size

    def add_packed(self, path: Path, size: int, *, verbose: bool) -> None:
        with self.lock:
            self.packed += 1
            self.packed_bytes += size
            ext = suffix_lower(path) or "<none>"
            self.packed_exts[ext] = self.packed_exts.get(ext, 0) + 1
            if verbose:
                print(f"packed:    {human_size(size):>10}  {path}")

    def add_optimized(self, path: Path, before: int, after: int) -> None:
        with self.lock:
            self.optimized += 1
            self.before_bytes += before
            self.after_bytes += after

    def add_skipped(self) -> None:
        with self.lock:
            self.skipped += 1

    def add_unsafe_skipped(self, path: Path, reason: str, *, verbose: bool) -> None:
        with self.lock:
            self.unsafe_skipped += 1
            self.unsafe_reasons[reason] = self.unsafe_reasons.get(reason, 0) + 1
            if verbose:
                print(f"guarded:   {reason:<28} {path}")

    def add_failed(self, path: Path, message: str) -> None:
        with self.lock:
            self.failed += 1
            print(f"failed: {path}: {message}", file=sys.stderr)

    def add_removed(self, path: Path, size: int, *, verbose: bool) -> None:
        with self.lock:
            self.removed += 1
            self.removed_bytes += size
            if verbose:
                print(f"removed:   {human_size(size):>10}  {path}")

    def add_file_result(self, result: FileResult, *, verbose: bool) -> None:
        with self.lock:
            self.processed += 1
            self.processed_bytes += result.before
            self.processed_after_bytes += result.after
            if result.status == "optimized":
                self.processed_optimized += 1
                self.optimized += 1
                self.before_bytes += result.before
                self.after_bytes += result.after
                if verbose:
                    print(
                        f"optimized: {human_size(result.before):>10} -> {human_size(result.after):>10} "
                            f"saved {human_size(result.saved):>10}  {result.path}"
                    )
            elif result.status == "failed":
                self.processed_failed += 1
                self.failed += 1
                print(f"failed: {result.path}: {result.message or 'unknown error'}", file=sys.stderr)
            else:
                self.processed_skipped += 1
                self.skipped += 1

    def add_resumed(self, entry: dict[str, object]) -> None:
        status = str(entry.get("status") or "unchanged")
        before = int(entry.get("before_size", 0) or 0)
        after = int(entry.get("after_size", before) or before)
        with self.lock:
            self.resumed += 1
            if status == "optimized":
                self.optimized += 1
                self.before_bytes += before
                self.after_bytes += after
            else:
                self.skipped += 1

    def snapshot(self) -> dict[str, int]:
        with self.lock:
            return {
                "candidates": self.candidates,
                "candidate_bytes": self.candidate_bytes,
                "optimized": self.optimized,
                "skipped": self.skipped,
                "failed": self.failed,
                "unsafe_skipped": self.unsafe_skipped,
                "before_bytes": self.before_bytes,
                "after_bytes": self.after_bytes,
                "processed": self.processed,
                "processed_bytes": self.processed_bytes,
                "processed_after_bytes": self.processed_after_bytes,
                "processed_optimized": self.processed_optimized,
                "processed_skipped": self.processed_skipped,
                "processed_failed": self.processed_failed,
                "resumed": self.resumed,
            }

    def packed_summary(self) -> str:
        with self.lock:
            return ", ".join(f"{ext}:{count}" for ext, count in sorted(self.packed_exts.items()))

    def guarded_summary(self) -> str:
        with self.lock:
            return ", ".join(f"{reason}:{count}" for reason, count in sorted(self.unsafe_reasons.items()))


def human_size(bytes_value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    value = float(bytes_value)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)}B"
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}TiB"


def save_ratio_text(before: int, after: int) -> str:
    saved = max(0, before - after)
    if before <= 0:
        return "0.0%"
    return f"{(saved / before) * 100:.1f}%"


def compression_ratio_text(before: int, after: int) -> str:
    if before <= 0:
        return "0.0%"
    return f"{(after / before) * 100:.1f}%"


def percent_text(part: int, whole: int) -> str:
    if whole <= 0:
        return "n/a"
    return f"{(part / whole) * 100:.2f}%"


def count_size_text(count: int, bytes_value: int) -> str:
    return f"{count} files / {human_size(bytes_value)}"


def progress_count_text(done: int, total: int | None) -> str:
    return f"{done}/{total if total is not None else '?'}"


def elapsed_text(started: float) -> str:
    seconds = max(0, int(time.monotonic() - started))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02}:{seconds:02}"


def print_kv_table(title: str, rows: list[tuple[str, str | None]]) -> None:
    rows = [(key, value) for key, value in rows if value]
    if not rows:
        return
    key_width = max(len("Metric"), *(len(key) for key, _ in rows))
    print(title)
    print(f"  {'Metric':<{key_width}}  Value")
    print(f"  {'-' * key_width}  -----")
    for key, value in rows:
        print(f"  {key:<{key_width}}  {value}")
    print()
    sys.stdout.flush()


def packed_media_dominates(stats: Stats) -> bool:
    return stats.packed_bytes > max(
        stats.candidate_bytes * LOW_VALUE_PACKED_MULTIPLIER,
        LOW_VALUE_PACKED_BYTES,
    )


def low_value_reason(stats: Stats, *, source_bytes: int) -> str | None:
    if stats.candidates == 0 or stats.candidate_bytes == 0:
        return "no loose optimizable media found"
    if packed_media_dominates(stats):
        return "packed containers dominate; loose-media optimization has limited effect"
    if source_bytes > 0 and stats.candidate_bytes / source_bytes < LOW_VALUE_MEDIA_RATIO:
        return f"loose optimizable media is only {percent_text(stats.candidate_bytes, source_bytes)} of source bytes"
    return None


@dataclass(frozen=True)
class EvaluationResult:
    stats: Stats
    source_bytes: int
    scanned: bool
    low_value_reason: str | None


class ProgressReporter:
    def __init__(self, settings: Settings, stats: Stats, *, total: int, total_bytes: int) -> None:
        self.settings = settings
        self.stats = stats
        self.total = total
        self.total_bytes = total_bytes
        self.mode = settings.progress
        self.last_print = 0.0
        self.started = time.monotonic()
        self.rich_progress = None
        self.task_id = None

    def __enter__(self) -> "ProgressReporter":
        if self.mode == "off" or self.total <= 0:
            return self
        if self.mode in {"auto", "rich"} and sys.stderr.isatty():
            try:
                from rich.console import Console
                from rich.progress import (
                    Progress,
                    SpinnerColumn,
                    TextColumn,
                    TimeElapsedColumn,
                )

                self.rich_progress = Progress(
                    SpinnerColumn("dots"),
                    TextColumn("[progress.description]{task.description}"),
                    TextColumn("{task.fields[count]}"),
                    TextColumn("saved {task.fields[saved_size]}"),
                    TextColumn("ratio {task.fields[ratio]}"),
                    TextColumn("original {task.fields[original_size]}"),
                    TimeElapsedColumn(),
                    console=Console(stderr=True),
                )
                self.rich_progress.start()
                self.task_id = self.rich_progress.add_task(
                    "optimizing",
                    total=self.total,
                    count=progress_count_text(0, self.total),
                    saved_size="0B",
                    ratio="0.0%",
                    original_size="0B",
                )
                return self
            except ImportError:
                if self.mode == "rich":
                    print("progress: rich is unavailable; falling back to plain progress", file=sys.stderr)
        if self.mode in {"plain", "rich"}:
            self._print_plain(force=True)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            self.update(force=True)
        if self.rich_progress is not None:
            self.rich_progress.stop()

    def update(self, *, force: bool = False) -> None:
        if self.mode == "off" or self.total <= 0:
            return
        snapshot = self.stats.snapshot()
        if self.rich_progress is not None and self.task_id is not None:
            processed_before = snapshot["processed_bytes"]
            processed_after = snapshot["processed_after_bytes"]
            self.rich_progress.update(
                self.task_id,
                completed=min(snapshot["processed"], self.total),
                count=progress_count_text(min(snapshot["processed"], self.total), self.total),
                saved_size=human_size(max(0, processed_before - processed_after)),
                ratio=compression_ratio_text(processed_before, processed_after),
                original_size=human_size(processed_before),
            )
            return
        self._print_plain(force=force)

    def _print_plain(self, *, force: bool) -> None:
        now = time.monotonic()
        if not force and now - self.last_print < PROGRESS_PRINT_INTERVAL:
            return
        self.last_print = now
        snapshot = self.stats.snapshot()
        before = snapshot["processed_bytes"]
        after = snapshot["processed_after_bytes"]
        print(
            "optimizing "
            f"{progress_count_text(min(snapshot['processed'], self.total), self.total)} | "
            f"{human_size(max(0, before - after))} saved | "
            f"ratio {compression_ratio_text(before, after)} | "
            f"original {human_size(before)} | "
            f"elapsed {elapsed_text(self.started)}",
            file=sys.stderr,
        )


def tree_size_snapshot(root: Path) -> tuple[int, int]:
    files = 0
    total = 0
    if not root.exists():
        return files, total
    for base, _, names in os.walk(root):
        for name in names:
            path = Path(base) / name
            try:
                total += path.stat().st_size
                files += 1
            except OSError:
                pass
    return files, total


class ExtractionReporter:
    def __init__(self, settings: Settings, dst: Path, *, total_files: int | None = None, total_bytes: int | None = None) -> None:
        self.settings = settings
        self.dst = dst
        self.total_files = total_files
        self.total_bytes = total_bytes
        self.mode = settings.progress
        self.last_update = 0.0
        self.started = time.monotonic()
        self.rich_progress = None
        self.task_id = None

    def __enter__(self) -> "ExtractionReporter":
        if self.mode == "off":
            return self
        if self.mode in {"auto", "rich"} and sys.stderr.isatty():
            try:
                from rich.console import Console
                from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

                self.rich_progress = Progress(
                    SpinnerColumn("dots"),
                    TextColumn("[progress.description]{task.description}"),
                    TextColumn("{task.fields[count]}"),
                    TextColumn("staged {task.fields[size]}/{task.fields[total_size]}"),
                    TimeElapsedColumn(),
                    console=Console(stderr=True),
                )
                self.rich_progress.start()
                self.task_id = self.rich_progress.add_task(
                    "extracting",
                    total=self.total_files,
                    count=progress_count_text(0, self.total_files),
                    size="0B",
                    total_size=human_size(self.total_bytes or 0) if self.total_bytes else "?",
                )
                return self
            except ImportError:
                if self.mode == "rich":
                    print("progress: rich is unavailable; falling back to plain progress", file=sys.stderr)
        if self.mode in {"plain", "rich"}:
            self.update(force=True)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.update(force=True)
        if self.rich_progress is not None:
            self.rich_progress.stop()

    def update(self, *, force: bool = False) -> None:
        if self.mode == "off":
            return
        now = time.monotonic()
        if not force and now - self.last_update < EXTRACTION_PROGRESS_INTERVAL:
            return
        self.last_update = now
        files, size = tree_size_snapshot(self.dst)
        if self.rich_progress is not None and self.task_id is not None:
            if self.total_files:
                self.rich_progress.update(
                    self.task_id,
                    completed=min(files, self.total_files),
                    count=progress_count_text(min(files, self.total_files), self.total_files),
                    size=human_size(size),
                )
            else:
                self.rich_progress.update(self.task_id, count=progress_count_text(files, None), size=human_size(size))
            return
        total_files = str(self.total_files) if self.total_files else "?"
        total_size = human_size(self.total_bytes) if self.total_bytes else "?"
        print(
            "extracting "
            f"{files}/{total_files} | "
            f"staged {human_size(size)}/{total_size} | "
            f"elapsed {elapsed_text(self.started)}",
            file=sys.stderr,
        )


class StepReporter:
    def __init__(self, settings: Settings, step: str, *, detail: str | None = None) -> None:
        self.settings = settings
        self.step = step
        self.detail = detail or ""
        self.mode = settings.progress
        self.started = time.monotonic()
        self.rich_progress = None
        self.task_id = None
        self.plain_started = False

    def __enter__(self) -> "StepReporter":
        if self.mode == "off":
            return self
        if self.mode in {"auto", "rich"} and sys.stderr.isatty():
            try:
                from rich.console import Console
                from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

                self.rich_progress = Progress(
                    SpinnerColumn("dots"),
                    TextColumn("[progress.description]{task.description}"),
                    TextColumn("{task.fields[detail]}"),
                    TimeElapsedColumn(),
                    console=Console(stderr=True),
                )
                self.rich_progress.start()
                self.task_id = self.rich_progress.add_task(self.step, total=None, detail=self.detail)
                return self
            except ImportError:
                if self.mode == "rich":
                    print("progress: rich is unavailable; falling back to plain progress", file=sys.stderr)
        if self.mode in {"plain", "rich"}:
            detail = f" {self.detail}" if self.detail else ""
            print(f"{self.step}{detail} | elapsed {elapsed_text(self.started)}", file=sys.stderr)
            self.plain_started = True
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.rich_progress is not None:
            self.rich_progress.stop()
        elif self.plain_started:
            status = "failed" if exc_type else "done"
            detail = f" {self.detail}" if self.detail else ""
            print(f"{self.step} {status}{detail} | elapsed {elapsed_text(self.started)}", file=sys.stderr)


def parse_positive_int(value: str) -> int:
    if value == "auto":
        return -1
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer or 'auto'") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def parse_nonnegative_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def parse_quality(value: str) -> int:
    parsed = parse_positive_int(value)
    if parsed == -1 or parsed > 100:
        raise argparse.ArgumentTypeError("must be between 1 and 100")
    return parsed


def parse_level(value: str, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"must be between {minimum} and {maximum}") from exc
    if parsed < minimum or parsed > maximum:
        raise argparse.ArgumentTypeError(f"must be between {minimum} and {maximum}")
    return parsed


def parse_zstd_level(value: str) -> int:
    return parse_level(value, 1, 19)


def parse_7z_level(value: str) -> int:
    parsed = parse_level(value, 0, 9)
    if parsed not in {0, 1, 3, 5, 7, 9}:
        raise argparse.ArgumentTypeError("7z level must be one of 0, 1, 3, 5, 7, or 9")
    return parsed


def parse_optional_int(value: str) -> int | None:
    if value.lower() in {"off", "none", "no"}:
        return None
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer or 'off'") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def parse_geometry(value: str) -> str:
    if not re.fullmatch(r"[1-9][0-9]*x[1-9][0-9]*", value):
        raise argparse.ArgumentTypeError("must look like 1920x1080")
    return value


def auto_jobs() -> int:
    cpu = os.cpu_count() or 4
    return max(1, min(8, max(2, (cpu * 2) // 3)))


def auto_extract_jobs() -> int:
    return max(1, os.cpu_count() or 4)


def auto_video_jobs(video_encoder: str) -> int:
    return 2 if video_encoder == "nvenc" else 1


def suffix_lower(path: Path) -> str:
    return path.suffix.lower()


def archive_suffix(path: Path) -> str | None:
    name = path.name.lower()
    for suffix in ARCHIVE_SUFFIXES:
        if name.endswith(suffix):
            return suffix
    return None


def unsupported_source_archive_suffix(path: Path) -> str | None:
    name = path.name.lower()
    for suffix in UNSUPPORTED_SOURCE_ARCHIVE_SUFFIXES:
        if name.endswith(suffix):
            return suffix
    return None


def archive_stem(path: Path) -> str:
    name = path.name
    lower = name.lower()
    for suffix in ARCHIVE_SUFFIXES + UNSUPPORTED_SOURCE_ARCHIVE_SUFFIXES:
        if lower.endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def is_extractable_archive(path: Path) -> bool:
    return path.is_file() and archive_suffix(path) is not None


def path_parts_lower(path: Path) -> tuple[str, ...]:
    return tuple(part.lower() for part in path.parts)


def relative_parts_lower(path: Path, root: Path | None) -> tuple[str, ...]:
    if root is None:
        return path_parts_lower(path)
    try:
        return path_parts_lower(path.relative_to(root))
    except ValueError:
        return path_parts_lower(path)


def has_unity_data_part(parts: tuple[str, ...]) -> bool:
    return any(part.endswith("_data") for part in parts)


@lru_cache(maxsize=128)
def has_html_integrity_manifest(root: Path | None) -> bool:
    if root is None or not root.is_dir():
        return False
    for base, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if not name.startswith(".")]
        lowered = {name.lower() for name in files}
        if lowered & HTML_INTEGRITY_MARKERS:
            return True
        if any(name.lower().startswith("precache-manifest") for name in files):
            return True
    return False


def detect_engines(root: Path) -> list[str]:
    if root.is_file():
        return ["archive"]
    engines: set[str] = set()
    candidates = [root]
    try:
        candidates.extend(child for child in root.iterdir() if child.is_dir())
    except OSError:
        pass

    for candidate in candidates:
        game = candidate / "game"
        if game.is_dir() and (
            any(game.glob("*.rpy"))
            or any(game.glob("*.rpyc"))
            or any(game.glob("*.rpa"))
            or (candidate / "renpy").is_dir()
        ):
            engines.add("renpy")
        www = candidate / "www"
        if (www / "data" / "System.json").is_file() or (www / "js" / "rpg_core.js").is_file():
            engines.add("rpg-maker")
        if any(child.is_dir() and child.name.endswith("_Data") for child in candidate.iterdir() if candidate.is_dir()):
            engines.add("unity")
        if (candidate / "index.html").is_file() or (www / "index.html").is_file():
            engines.add("html")
        if any(candidate.glob("*.xp3")):
            engines.add("kirikiri")
    return sorted(engines) or ["unknown"]


def guard_reason(path: Path, root: Path | None, settings: Settings) -> str | None:
    ext = suffix_lower(path)
    parts = relative_parts_lower(path, root)
    policy = settings.engine_policy

    if ext in RPGM_ENCRYPTED_EXTS:
        return "rpgm-encrypted-asset"
    if ext in UNITY_PACKED_EXTS:
        return "unity-packed-asset"
    if MANIFEST_NAME in parts:
        return "manifest"
    if any(part in {"__macosx", "__pycache__", ".git", ".svn"} for part in parts):
        return "metadata-dir"

    if policy == "aggressive":
        return None

    if has_unity_data_part(parts):
        return "unity-data-dir"
    if any(part in UNITY_SKIP_DIR_NAMES for part in parts):
        return "unity-resource-dir"
    if any(part in HTML_SKIP_DIRS for part in parts):
        return "html-cache-or-build-dir"
    if ext in OPTIMIZABLE_EXTS and has_html_integrity_manifest(root):
        return "html-integrity-manifest"

    if "game" in parts:
        game_index = parts.index("game")
        after_game = parts[game_index + 1 :]
        if after_game and after_game[0] == "cache":
            return "renpy-cache"
        if policy == "safe" and ext in IMAGE_EXTS and after_game[:1] == ("gui",):
            return "renpy-gui"

    if "img" in parts and ext in IMAGE_EXTS:
        img_index = parts.index("img")
        img_group = parts[img_index + 1] if len(parts) > img_index + 1 else ""
        if img_group in RPGM_SPRITE_DIRS:
            return "rpgm-sprite-or-ui"
        if policy == "safe" and img_group not in RPGM_SAFE_IMAGE_DIRS:
            return "rpgm-unclassified-image"

    return None


def category_for(path: Path, settings: Settings) -> str | None:
    ext = suffix_lower(path)
    if ext in IMAGE_EXTS and not settings.skip_images:
        return "image"
    if ext in AUDIO_EXTS and not settings.skip_audio:
        return "audio"
    if ext in VIDEO_EXTS and not settings.skip_video:
        return "video"
    if ext in PACKED_EXTS:
        return "packed"
    return None


def tree_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                pass
    return total


def newest_mtime_ns(path: Path) -> int:
    if path.is_file():
        return path.stat().st_mtime_ns
    newest = 0
    for file in iter_files(path):
        try:
            newest = max(newest, file.stat().st_mtime_ns)
        except OSError:
            pass
    return newest


def hash_file(path: Path, mode: str) -> tuple[str, str | None]:
    size = path.stat().st_size
    if mode == "none":
        return "none", None
    effective = mode
    if mode == "auto":
        effective = "full" if size <= AUTO_FULL_HASH_LIMIT else "partial"
    digest = hashlib.sha256()
    if effective == "full":
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return "full", digest.hexdigest()
    if effective == "partial":
        digest.update(str(size).encode("utf-8"))
        with path.open("rb") as handle:
            digest.update(handle.read(PARTIAL_HASH_BYTES))
            if size > PARTIAL_HASH_BYTES:
                handle.seek(max(0, size - PARTIAL_HASH_BYTES))
                digest.update(handle.read(PARTIAL_HASH_BYTES))
        return "partial", digest.hexdigest()
    raise ToolError(f"unknown hash mode: {mode}")


def fingerprint_path(path: Path, mode: str) -> dict[str, object]:
    path = path.resolve()
    if path.is_file():
        stat = path.stat()
        hash_kind, digest = hash_file(path, mode)
        return {
            "kind": "file",
            "name": path.name,
            "bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "hash_mode": hash_kind,
            "sha256": digest,
        }

    total = 0
    count = 0
    newest = 0
    digest = hashlib.sha256()
    full_content = mode == "full"
    for file in sorted(iter_files(path), key=lambda item: str(item.relative_to(path))):
        try:
            stat = file.stat()
        except OSError:
            continue
        relative = file.relative_to(path).as_posix()
        total += stat.st_size
        count += 1
        newest = max(newest, stat.st_mtime_ns)
        digest.update(relative.encode("utf-8", "surrogateescape"))
        digest.update(b"\0")
        digest.update(str(stat.st_size).encode("ascii"))
        digest.update(b"\0")
        digest.update(str(stat.st_mtime_ns).encode("ascii"))
        digest.update(b"\0")
        if full_content:
            with file.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            digest.update(b"\0")

    return {
        "kind": "directory",
        "name": path.name,
        "bytes": total,
        "files": count,
        "mtime_ns": newest,
        "hash_mode": "full" if full_content else "metadata",
        "sha256": digest.hexdigest() if mode != "none" else None,
    }


def manifest_path_for_directory(path: Path) -> Path:
    return path / MANIFEST_NAME


def manifest_path_for_archive(path: Path) -> Path:
    return path.with_name(path.name + ".vnopt-manifest.json")


def read_manifest(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def write_manifest(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, path)


def stable_json(data: object) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def settings_signature(settings: Settings) -> dict[str, object]:
    return {
        "profile_max_size": settings.max_size,
        "jpeg_quality": settings.jpeg_quality,
        "webp_quality": settings.webp_quality,
        "ogg_quality": settings.ogg_quality,
        "mp3_bitrate": settings.mp3_bitrate,
        "video_crf": settings.video_crf,
        "webm_crf": settings.webm_crf,
        "engine_policy": settings.engine_policy,
        "strip_pc_runtime": settings.strip_pc_runtime,
        "strip_cache": settings.strip_cache,
        "skip_images": settings.skip_images,
        "skip_audio": settings.skip_audio,
        "skip_video": settings.skip_video,
        "archive_format": settings.archive_format,
        "zstd_level": settings.zstd_level,
        "zstd_long": settings.zstd_long,
        "sevenzip_level": settings.sevenzip_level,
    }


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")
    return slug[:72] or "source"


def work_id(settings: Settings, source_fingerprint: dict[str, object]) -> str:
    stem = archive_stem(settings.source) if settings.source.is_file() else settings.source.name
    payload = {
        "command": settings.command,
        "source": str(settings.source),
        "source_fingerprint": source_fingerprint,
        "settings": settings_signature(settings),
    }
    digest = hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()[:12]
    return f"{slugify(stem)}-{settings.command}-{digest}"


def default_work_root(settings: Settings, source_fingerprint: dict[str, object]) -> Path:
    return settings.source.parent / WORK_BASE_NAME / work_id(settings, source_fingerprint)


def resolve_work_root(settings: Settings, source_fingerprint: dict[str, object]) -> Path:
    if settings.work_dir:
        return settings.work_dir.expanduser().resolve()
    return default_work_root(settings, source_fingerprint)


def file_identity(path: Path, settings: Settings) -> dict[str, object]:
    stat = path.stat()
    identity: dict[str, object] = {
        "bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": None,
        "hash_mode": "none",
    }
    if settings.hash_mode == "none" or stat.st_size > WORK_FILE_FULL_HASH_LIMIT:
        return identity
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    identity["sha256"] = digest.hexdigest()
    identity["hash_mode"] = "full"
    return identity


def cleanup_partial_outputs(root: Path) -> None:
    if not root.exists():
        return
    for path in root.rglob("*"):
        if path.is_file() and (".vnopt." in path.name or (path.name.startswith(".") and path.name.endswith(".tmp"))):
            path.unlink(missing_ok=True)


class WorkState:
    def __init__(
        self,
        work_root: Path,
        settings: Settings,
        source_fingerprint: dict[str, object],
        *,
        source_is_archive: bool,
    ) -> None:
        self.work_root = work_root
        self.path = work_root / WORK_MANIFEST_NAME
        self.settings = settings
        self.source_fingerprint = source_fingerprint
        self.source_is_archive = source_is_archive
        self.lock = threading.Lock()
        self.data = self._load_or_new()

    def _new(self) -> dict[str, object]:
        return {
            "schema": "vn-optimize-assets-work",
            "version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "command": self.settings.command,
            "source": str(self.settings.source),
            "source_is_archive": self.source_is_archive,
            "settings": settings_signature(self.settings),
            "source_fingerprint": self.source_fingerprint,
            "staged": False,
            "stage_mode": None,
            "entries": {},
        }

    def _matches(self, data: dict[str, object]) -> bool:
        return (
            data.get("schema") == "vn-optimize-assets-work"
            and data.get("command") == self.settings.command
            and data.get("source") == str(self.settings.source)
            and data.get("settings") == settings_signature(self.settings)
            and data.get("source_fingerprint") == self.source_fingerprint
        )

    def _load_or_new(self) -> dict[str, object]:
        existing = read_manifest(self.path)
        if self.settings.resume and existing and self._matches(existing):
            entries = existing.get("entries")
            if not isinstance(entries, dict):
                existing["entries"] = {}
            return existing
        if existing and self.work_root.exists() and any(self.work_root.iterdir()):
            if not self.settings.clean_work_dir and self.settings.work_dir:
                raise ToolError("--work-dir contains state for another source/settings; pass --clean-work-dir")
            shutil.rmtree(self.work_root)
            self.work_root.mkdir(parents=True, exist_ok=True)
        return self._new()

    def save(self) -> None:
        with self.lock:
            self.data["updated_at"] = datetime.now(timezone.utc).isoformat()
            write_manifest(self.path, self.data)

    def staged(self, mode: str) -> bool:
        return bool(self.data.get("staged")) and self.data.get("stage_mode") == mode

    def mark_staged(self, mode: str) -> None:
        with self.lock:
            self.data["staged"] = True
            self.data["stage_mode"] = mode
            self.data["updated_at"] = datetime.now(timezone.utc).isoformat()
            write_manifest(self.path, self.data)

    def entry_done(self, root: Path, path: Path, current_identity: dict[str, object]) -> dict[str, object] | None:
        entries = self.data.get("entries")
        if not self.settings.resume or not isinstance(entries, dict):
            return None
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            return None
        entry = entries.get(rel)
        if not isinstance(entry, dict):
            return None
        if entry.get("status") not in {"optimized", "unchanged"}:
            return None
        if entry.get("after_identity") != current_identity:
            return None
        return entry

    def record(self, root: Path, task: OptimizationTask, result: FileResult) -> None:
        try:
            rel = result.path.relative_to(root).as_posix()
        except ValueError:
            rel = result.path.as_posix()
        try:
            after_identity = file_identity(result.path, self.settings)
        except OSError:
            after_identity = task.before_identity
        entry = {
            "status": result.status,
            "before_size": result.before,
            "after_size": result.after,
            "saved_bytes": result.saved,
            "before_identity": task.before_identity,
            "after_identity": after_identity,
            "message": result.message,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with self.lock:
            entries = self.data.setdefault("entries", {})
            if isinstance(entries, dict):
                entries[rel] = entry
            self.data["updated_at"] = datetime.now(timezone.utc).isoformat()
            write_manifest(self.path, self.data)


def build_manifest(
    *,
    command: str,
    source: Path,
    output: Path,
    settings: Settings,
    stats: Stats,
    source_fingerprint: dict[str, object],
    output_fingerprint: dict[str, object],
    archive: Path | None = None,
    archive_fingerprint: dict[str, object] | None = None,
) -> dict[str, object]:
    before = int(source_fingerprint.get("bytes", 0) or 0)
    after = int(output_fingerprint.get("bytes", 0) or 0)
    ratio = (after / before) if before else None
    return {
        "schema": "vn-optimize-assets",
        "version": MANIFEST_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "source": str(source),
        "output": str(output),
        "archive": str(archive) if archive else None,
        "settings": settings_signature(settings),
        "source_fingerprint": source_fingerprint,
        "output_fingerprint": output_fingerprint,
        "archive_fingerprint": archive_fingerprint,
        "before_bytes": before,
        "after_bytes": after,
        "compression_ratio": ratio,
        "saved_bytes": before - after,
        "stats": {
            "candidates": stats.candidates,
            "candidate_bytes": stats.candidate_bytes,
            "packed": stats.packed,
            "packed_bytes": stats.packed_bytes,
            "packed_by_extension": dict(sorted(stats.packed_exts.items())),
            "optimized": stats.optimized,
            "skipped": stats.skipped,
            "guarded_engine_skips": stats.unsafe_skipped,
            "guarded_by_reason": dict(sorted(stats.unsafe_reasons.items())),
            "failed": stats.failed,
            "processed": stats.processed,
            "processed_bytes": stats.processed_bytes,
            "processed_after_bytes": stats.processed_after_bytes,
            "processed_optimized": stats.processed_optimized,
            "processed_skipped": stats.processed_skipped,
            "processed_failed": stats.processed_failed,
            "resumed": stats.resumed,
            "removed": stats.removed,
            "removed_bytes": stats.removed_bytes,
        },
        "detected_engines": detect_engines(output if output.is_dir() else source),
    }


def manifest_matches_source(
    manifest: dict[str, object] | None,
    source_fingerprint: dict[str, object],
    settings: Settings,
    *,
    command: str,
) -> bool:
    if not manifest:
        return False
    if manifest.get("schema") != "vn-optimize-assets":
        return False
    if manifest.get("command") != command:
        return False
    if manifest.get("settings") != settings_signature(settings):
        return False
    return manifest.get("source_fingerprint") == source_fingerprint


def manifest_matches_output(
    manifest: dict[str, object] | None,
    output_fingerprint: dict[str, object],
    settings: Settings,
) -> bool:
    if not manifest:
        return False
    if manifest.get("schema") != "vn-optimize-assets":
        return False
    if manifest.get("settings") != settings_signature(settings):
        return False
    return manifest.get("output_fingerprint") == output_fingerprint


def ensure_empty_or_missing(path: Path) -> None:
    if not path.exists():
        return
    if not path.is_dir():
        raise ToolError(f"destination exists and is not a directory: {path}")
    try:
        next(path.iterdir())
    except StopIteration:
        return
    raise ToolError(f"destination already exists and is not empty: {path}")


def ensure_dst_not_inside_src(src: Path, dst: Path) -> None:
    try:
        dst.resolve().relative_to(src.resolve())
    except ValueError:
        return
    raise ToolError("--dst cannot be inside --source; use a sibling output directory")


def run_quiet(command: list[str], *, env: dict[str, str] | None = None) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        check=False,
    )
    return completed.returncode, completed.stderr.strip()


def magick_env(settings: Settings) -> dict[str, str]:
    env = os.environ.copy()
    env["MAGICK_THREAD_LIMIT"] = str(settings.magick_threads)
    return env


def ffmpeg_common_input(file: Path) -> list[str]:
    return ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(file)]


def tmp_for(path: Path) -> Path:
    return path.with_name(f".{path.name}.vnopt.{os.getpid()}.{threading.get_ident()}{path.suffix}")


def image_frame_count(path: Path, settings: Settings) -> int:
    completed = subprocess.run(
        ["magick", "identify", "-format", "%n\n", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
        env=magick_env(settings),
    )
    if completed.returncode != 0:
        return 1
    first = completed.stdout.splitlines()[0:1]
    if not first:
        return 1
    try:
        return int(first[0])
    except ValueError:
        return 1


def unchanged_result(path: Path, before: int | None = None, message: str | None = None) -> FileResult:
    try:
        size = path.stat().st_size if before is None else before
    except OSError:
        size = 0
    return FileResult(path=path, status="unchanged", before=size, after=size, message=message)


def failed_result(path: Path, before: int, message: str) -> FileResult:
    return FileResult(path=path, status="failed", before=before, after=before, message=message)


def replace_if_smaller(path: Path, tmp: Path) -> FileResult:
    try:
        before = path.stat().st_size
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        return failed_result(path, 0, str(exc))

    if not tmp.exists() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        return unchanged_result(path, before, "empty optimizer output")

    after = tmp.stat().st_size
    if after < before:
        try:
            shutil.copystat(path, tmp)
        except OSError:
            pass
        os.replace(tmp, path)
        return FileResult(path=path, status="optimized", before=before, after=after)

    tmp.unlink(missing_ok=True)
    return unchanged_result(path, before)


def optimize_jpeg(path: Path, settings: Settings) -> FileResult:
    before = path.stat().st_size
    tmp = tmp_for(path)
    command = [
        "magick",
        str(path),
        "-auto-orient",
        "-resize",
        f"{settings.max_size}>",
        "-strip",
        "-sampling-factor",
        "4:2:0",
        "-interlace",
        "Plane",
        "-quality",
        str(settings.jpeg_quality),
        str(tmp),
    ]
    status, error = run_quiet(command, env=magick_env(settings))
    if status != 0:
        tmp.unlink(missing_ok=True)
        return failed_result(path, before, error or "magick failed")
    return replace_if_smaller(path, tmp)


def optimize_png(path: Path, settings: Settings) -> FileResult:
    before = path.stat().st_size
    if image_frame_count(path, settings) > 1:
        return unchanged_result(path, before, "multi-frame image")
    tmp = tmp_for(path)
    command = [
        "magick",
        str(path),
        "-resize",
        f"{settings.max_size}>",
        "-strip",
        "-define",
        "png:compression-level=9",
        "-define",
        "png:compression-filter=5",
        str(tmp),
    ]
    status, error = run_quiet(command, env=magick_env(settings))
    if status != 0:
        tmp.unlink(missing_ok=True)
        return failed_result(path, before, error or "magick failed")
    return replace_if_smaller(path, tmp)


def optimize_webp(path: Path, settings: Settings) -> FileResult:
    before = path.stat().st_size
    if image_frame_count(path, settings) > 1:
        return unchanged_result(path, before, "multi-frame image")
    tmp = tmp_for(path)
    command = [
        "magick",
        str(path),
        "-resize",
        f"{settings.max_size}>",
        "-strip",
        "-quality",
        str(settings.webp_quality),
        str(tmp),
    ]
    status, error = run_quiet(command, env=magick_env(settings))
    if status != 0:
        tmp.unlink(missing_ok=True)
        return failed_result(path, before, error or "magick failed")
    return replace_if_smaller(path, tmp)


def optimize_ogg(path: Path, settings: Settings) -> FileResult:
    before = path.stat().st_size
    tmp = tmp_for(path)
    command = [
        *ffmpeg_common_input(path),
        "-vn",
        "-map_metadata",
        "-1",
        "-c:a",
        "libvorbis",
        "-q:a",
        str(settings.ogg_quality),
        str(tmp),
    ]
    status, error = run_quiet(command)
    if status != 0:
        tmp.unlink(missing_ok=True)
        return failed_result(path, before, error or "ffmpeg failed")
    return replace_if_smaller(path, tmp)


def optimize_mp3(path: Path, settings: Settings) -> FileResult:
    before = path.stat().st_size
    tmp = tmp_for(path)
    command = [
        *ffmpeg_common_input(path),
        "-vn",
        "-map_metadata",
        "-1",
        "-c:a",
        "libmp3lame",
        "-b:a",
        settings.mp3_bitrate,
        str(tmp),
    ]
    status, error = run_quiet(command)
    if status != 0:
        tmp.unlink(missing_ok=True)
        return failed_result(path, before, error or "ffmpeg failed")
    return replace_if_smaller(path, tmp)


def optimize_wav(path: Path, settings: Settings) -> FileResult:
    before = path.stat().st_size
    tmp = tmp_for(path)
    command = [
        *ffmpeg_common_input(path),
        "-vn",
        "-map_metadata",
        "-1",
        "-c:a",
        "pcm_s16le",
        "-ar",
        "44100",
        str(tmp),
    ]
    status, error = run_quiet(command)
    if status != 0:
        tmp.unlink(missing_ok=True)
        return failed_result(path, before, error or "ffmpeg failed")
    return replace_if_smaller(path, tmp)


@lru_cache(maxsize=1)
def ffmpeg_encoders() -> str:
    if not process.command_exists("ffmpeg"):
        return ""
    completed = subprocess.run(
        ["ffmpeg", "-hide_banner", "-encoders"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout


def has_ffmpeg_encoder(name: str) -> bool:
    return name in ffmpeg_encoders()


def selected_video_encoder(settings: Settings) -> str:
    if settings.video_encoder == "nvenc":
        if not has_ffmpeg_encoder("h264_nvenc"):
            raise ToolError("ffmpeg does not expose h264_nvenc; use --video-encoder x264")
        return "nvenc"
    if settings.video_encoder == "auto":
        if process.command_exists("nvidia-smi") and has_ffmpeg_encoder("h264_nvenc"):
            return "nvenc"
        return "x264"
    return "x264"


def video_scale_filter(settings: Settings) -> str:
    width, height = settings.max_size.split("x", 1)
    return (
        f"scale=w={width}:h={height}:"
        "force_original_aspect_ratio=decrease:force_divisible_by=2,format=yuv420p"
    )


def optimize_h264_video(path: Path, settings: Settings, encoder: str) -> FileResult:
    before = path.stat().st_size
    tmp = tmp_for(path)
    command = [
        *ffmpeg_common_input(path),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-dn",
        "-sn",
        "-map_metadata",
        "-1",
        "-vf",
        video_scale_filter(settings),
    ]
    if encoder == "nvenc":
        command.extend(
            [
                "-c:v",
                "h264_nvenc",
                "-preset",
                settings.nvenc_preset,
                "-rc",
                "vbr",
                "-cq:v",
                str(settings.video_crf),
                "-b:v",
                "0",
            ]
        )
    else:
        command.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                settings.video_preset,
                "-crf",
                str(settings.video_crf),
                "-threads",
                str(settings.ffmpeg_threads),
            ]
        )
    command.extend(["-c:a", "aac", "-b:a", settings.mp3_bitrate, "-movflags", "+faststart", str(tmp)])
    status, error = run_quiet(command)
    if status != 0:
        tmp.unlink(missing_ok=True)
        return failed_result(path, before, error or "ffmpeg failed")
    return replace_if_smaller(path, tmp)


def optimize_webm_video(path: Path, settings: Settings) -> FileResult:
    before = path.stat().st_size
    tmp = tmp_for(path)
    command = [
        *ffmpeg_common_input(path),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-dn",
        "-sn",
        "-map_metadata",
        "-1",
        "-vf",
        video_scale_filter(settings),
        "-c:v",
        "libvpx-vp9",
        "-crf",
        str(settings.webm_crf),
        "-b:v",
        "0",
        "-deadline",
        "good",
        "-cpu-used",
        "4",
        "-row-mt",
        "1",
        "-threads",
        str(settings.ffmpeg_threads),
        "-c:a",
        "libopus",
        "-b:a",
        settings.mp3_bitrate,
        str(tmp),
    ]
    status, error = run_quiet(command)
    if status != 0:
        tmp.unlink(missing_ok=True)
        return failed_result(path, before, error or "ffmpeg failed")
    return replace_if_smaller(path, tmp)


class Optimizer:
    def __init__(self, settings: Settings, stats: Stats) -> None:
        self.settings = settings
        self.stats = stats
        encoder = selected_video_encoder(settings) if not settings.skip_video else "x264"
        self.video_encoder = encoder
        self.video_gate = threading.BoundedSemaphore(settings.video_jobs)

    def optimize_path(self, path: Path) -> FileResult:
        try:
            size = path.stat().st_size
        except OSError as exc:
            return failed_result(path, 0, str(exc))
        try:
            ext = suffix_lower(path)
            if ext in {".jpg", ".jpeg"}:
                return optimize_jpeg(path, self.settings)
            elif ext == ".png":
                return optimize_png(path, self.settings)
            elif ext == ".webp":
                return optimize_webp(path, self.settings)
            elif ext == ".ogg":
                return optimize_ogg(path, self.settings)
            elif ext == ".mp3":
                return optimize_mp3(path, self.settings)
            elif ext == ".wav":
                return optimize_wav(path, self.settings)
            elif ext in VIDEO_EXTS:
                with self.video_gate:
                    if ext == ".webm":
                        return optimize_webm_video(path, self.settings)
                    return optimize_h264_video(path, self.settings, self.video_encoder)
        except OSError as exc:
            return failed_result(path, size, str(exc))
        return unchanged_result(path, size)


def iter_files(root: Path):
    for base, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if not name.startswith(".")]
        for name in files:
            if ".vnopt." in name or name in {MANIFEST_NAME, WORK_MANIFEST_NAME}:
                continue
            yield Path(base) / name


def scan_directory(root: Path, settings: Settings, stats: Stats) -> None:
    for path in iter_files(root):
        category = category_for(path, settings)
        if category is None:
            continue
        reason = guard_reason(path, root, settings)
        if reason:
            stats.add_unsafe_skipped(path, reason, verbose=settings.verbose)
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if category == "packed":
            stats.add_packed(path, size, verbose=settings.verbose)
            continue
        stats.add_candidate(size)
        if settings.verbose:
            print(f"candidate: {human_size(size):>10}  {path}")


def discover_optimization_tasks(
    root: Path,
    settings: Settings,
    stats: Stats,
    work_state: WorkState | None,
) -> list[OptimizationTask]:
    tasks: list[OptimizationTask] = []
    for path in iter_files(root):
        category = category_for(path, settings)
        if category is None:
            continue
        reason = guard_reason(path, root, settings)
        if reason:
            stats.add_unsafe_skipped(path, reason, verbose=settings.verbose)
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if category == "packed":
            stats.add_packed(path, size, verbose=settings.verbose)
            continue
        stats.add_candidate(size)
        try:
            identity = file_identity(path, settings)
        except OSError as exc:
            stats.add_failed(path, str(exc))
            continue
        if work_state is not None:
            entry = work_state.entry_done(root, path, identity)
            if entry is not None:
                stats.add_resumed(entry)
                continue
        tasks.append(OptimizationTask(path=path, before_identity=identity))
    return tasks


def print_optimization_plan(stats: Stats, *, remaining: int, remaining_bytes: int) -> None:
    rows: list[tuple[str, str | None]] = [
        (
            "Queue",
            f"{remaining}/{stats.candidates} files / {human_size(remaining_bytes)}/{human_size(stats.candidate_bytes)} media",
        )
    ]
    if stats.resumed:
        rows.append(("Resumed", f"{stats.resumed} files"))
    if stats.packed:
        packed = stats.packed_summary()
        rows.append(("Packed skipped", count_size_text(stats.packed, stats.packed_bytes) + (f" ({packed})" if packed else "")))
    if stats.unsafe_skipped:
        guarded = stats.guarded_summary()
        rows.append(("Guarded skips", f"{stats.unsafe_skipped} files" + (f" ({guarded})" if guarded else "")))
    if stats.candidates == 0:
        rows.append(("Note", "no loose image/audio/video files found"))
    elif remaining == 0:
        rows.append(("Note", "no files need processing in this run"))
    print_kv_table("Optimization", rows)


def run_parallel(root: Path, settings: Settings, stats: Stats, work_state: WorkState | None = None) -> None:
    optimizer = Optimizer(settings, stats)
    tasks = discover_optimization_tasks(root, settings, stats, work_state)
    task_bytes = sum(int(task.before_identity.get("bytes", 0) or 0) for task in tasks)
    print_optimization_plan(stats, remaining=len(tasks), remaining_bytes=task_bytes)
    futures: dict[concurrent.futures.Future[FileResult], OptimizationTask] = {}
    verbose_results = settings.verbose and settings.progress == "off"
    with concurrent.futures.ThreadPoolExecutor(max_workers=settings.jobs) as pool:
        with ProgressReporter(settings, stats, total=len(tasks), total_bytes=task_bytes) as progress:
            for task in tasks:
                futures[pool.submit(optimizer.optimize_path, task.path)] = task
            for future in concurrent.futures.as_completed(futures):
                task = futures[future]
                try:
                    result = future.result()
                except Exception as exc:  # pragma: no cover - defensive worker boundary
                    result = failed_result(task.path, int(task.before_identity.get("bytes", 0) or 0), str(exc))
                stats.add_file_result(result, verbose=verbose_results)
                if work_state is not None:
                    work_state.record(root, task, result)
                progress.update()


def archive_extension(archive_format: str) -> str:
    if archive_format == "tar.zst":
        return ".tar.zst"
    if archive_format == "7z":
        return ".7z"
    raise ToolError(f"unsupported archive format: {archive_format}")


def default_archive_path(source: Path, archive_format: str) -> Path:
    suffix = archive_extension(archive_format)
    if source.is_file():
        return source.parent / f"{archive_stem(source)}-optimized{suffix}"
    return source.with_name(f"{source.name}-optimized{suffix}")


def source_has_archive_format(source: Path, archive_format: str) -> bool:
    return source.is_file() and source.name.lower().endswith(archive_extension(archive_format))


def resolve_archive_output(settings: Settings) -> Path:
    if settings.output_archive:
        return settings.output_archive.expanduser()
    if settings.dst:
        dst = settings.dst.expanduser()
        if dst.suffix or archive_suffix(dst):
            return dst
        return dst / default_archive_path(settings.source, settings.archive_format).name
    return default_archive_path(settings.source, settings.archive_format)


def skip_existing_archive_if_current(settings: Settings, archive: Path, source_fingerprint: dict[str, object]) -> bool:
    if settings.force:
        return False
    if source_has_archive_format(settings.source, settings.archive_format):
        print(f"skip: source already uses optimized archive format: {settings.source}")
        return True
    if not settings.manifest or not archive.exists():
        return False
    manifest = read_manifest(manifest_path_for_archive(archive))
    if manifest_matches_source(manifest, source_fingerprint, settings, command="repack"):
        print(f"skip: optimized archive already exists for this source/settings: {archive}")
        return True
    return False


def source_root_for_archive(work_dir: Path) -> tuple[Path, Path]:
    entries = [entry for entry in work_dir.iterdir() if entry.name != MANIFEST_NAME]
    dirs = [entry for entry in entries if entry.is_dir()]
    if len(entries) == 1 and dirs:
        root = dirs[0]
        return root.parent, root
    return work_dir.parent, work_dir


def create_tar_zst(source_dir: Path, output: Path, settings: Settings) -> None:
    process.require("tar", "zstd")
    output.parent.mkdir(parents=True, exist_ok=True)
    parent, item = source_root_for_archive(source_dir)
    command_zstd = ["zstd", f"-{settings.zstd_level}", "-T0", "-q", "-o", str(output), "-"]
    if settings.zstd_long:
        command_zstd.insert(1, f"--long={settings.zstd_long}")

    with subprocess.Popen(
        ["tar", "-cf", "-", "-C", str(parent), item.name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as tar_proc:
        zstd_proc = subprocess.Popen(
            command_zstd,
            stdin=tar_proc.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        if tar_proc.stdout:
            tar_proc.stdout.close()
        _, tar_stderr = tar_proc.communicate()
        _, zstd_stderr = zstd_proc.communicate()
        if tar_proc.returncode != 0:
            output.unlink(missing_ok=True)
            raise ToolError(tar_stderr.decode("utf-8", "replace").strip() or "tar failed")
        if zstd_proc.returncode != 0:
            output.unlink(missing_ok=True)
            raise ToolError(zstd_stderr.strip() or "zstd failed")


def create_7z(source_dir: Path, output: Path, settings: Settings) -> None:
    process.require("7z")
    output.parent.mkdir(parents=True, exist_ok=True)
    parent, item = source_root_for_archive(source_dir)
    command = [
        "7z",
        "a",
        "-t7z",
        f"-mx={settings.sevenzip_level}",
        "-m0=LZMA2",
        f"-mmt={settings.extract_jobs}",
        "-ms=on",
        str(output),
        item.name,
    ]
    completed = subprocess.run(
        command,
        cwd=parent,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        output.unlink(missing_ok=True)
        raise ToolError(completed.stderr.strip() or "7z compression failed")


def create_archive(source_dir: Path, output: Path, settings: Settings) -> None:
    if output.exists() and not settings.force:
        raise ToolError(f"archive already exists: {output}")
    tmp = output.with_name(f".{output.name}.tmp")
    tmp.unlink(missing_ok=True)
    try:
        with StepReporter(settings, "archiving", detail=output.name):
            if settings.archive_format == "tar.zst":
                create_tar_zst(source_dir, tmp, settings)
            elif settings.archive_format == "7z":
                create_7z(source_dir, tmp, settings)
            else:
                raise ToolError(f"unsupported archive format: {settings.archive_format}")
        os.replace(tmp, output)
    except KeyboardInterrupt:
        tmp.unlink(missing_ok=True)
        raise


def copy_source_as_child(source: Path, dst_root: Path) -> Path:
    target = dst_root / source.name
    ensure_empty_or_missing(target)
    copy_source_tree(source, target)
    return target


def find_extractor(archive: Path, extract_jobs: int) -> list[str]:
    suffix = archive_suffix(archive)
    if suffix is None:
        raise ToolError(f"unsupported archive type: {archive}")

    if suffix.startswith(".tar") or suffix in {".tgz", ".tbz2", ".txz"}:
        if process.command_exists("bsdtar"):
            return ["bsdtar", "-xf", str(archive)]
        if process.command_exists("tar"):
            return ["tar", "-xf", str(archive)]

    if process.command_exists("7z"):
        return ["7z", "x", "-y", f"-mmt={extract_jobs}", str(archive)]

    if suffix == ".zip" and process.command_exists("unzip"):
        return ["unzip", "-q", "-o", str(archive)]

    raise ToolError("missing archive extractor; install p7zip or libarchive")


def extract_archive(archive: Path, dst: Path, settings: Settings) -> subprocess.Popen[str]:
    dst.mkdir(parents=True, exist_ok=True)
    command = find_extractor(archive, settings.extract_jobs)
    if command[0] in {"bsdtar", "tar"}:
        command.extend(["-C", str(dst)])
    elif command[0] == "7z":
        command.insert(4, f"-o{dst}")
    else:
        command.extend(["-d", str(dst)])

    return subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )


def terminate_process(process_handle: subprocess.Popen[str]) -> None:
    if process_handle.poll() is not None:
        return
    try:
        os.killpg(process_handle.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except OSError:
        process_handle.terminate()
    try:
        process_handle.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process_handle.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        except OSError:
            process_handle.kill()
        process_handle.wait()


def game_roots(root: Path) -> list[Path]:
    roots: list[Path] = []
    if (root / "game").is_dir():
        roots.append(root)
    for child in root.iterdir() if root.is_dir() else ():
        if child.is_dir() and (child / "game").is_dir():
            roots.append(child)
    return roots or [root]


def remove_path(path: Path) -> int:
    size = tree_size(path)
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
    return size


def strip_android_extras(root: Path, settings: Settings, stats: Stats) -> None:
    targets: list[Path] = []
    for game_root in game_roots(root):
        if settings.strip_pc_runtime:
            for pattern in ("*.exe", "*.bat", "*.cmd", "*.ps1", "*.sh", "*.dll", "*.dylib"):
                targets.extend(game_root.glob(pattern))
            lib_dir = game_root / "lib"
            if lib_dir.is_dir():
                targets.append(lib_dir)
        if settings.strip_cache:
            cache_dir = game_root / "game" / "cache"
            if cache_dir.is_dir():
                targets.append(cache_dir)

    unique_targets = sorted({target.resolve(): target for target in targets if target.exists()}.values())
    for target in unique_targets:
        try:
            size = remove_path(target)
        except OSError as exc:
            stats.add_failed(target, str(exc))
            continue
        stats.add_removed(target, size, verbose=settings.verbose)


def archive_scan_entries(archive: Path) -> list[tuple[str, int, bool]]:
    if not process.command_exists("7z"):
        return []
    completed = subprocess.run(
        ["7z", "l", "-slt", str(archive)],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return []
    entries: list[tuple[str, int, bool]] = []
    current: dict[str, str] = {}
    for line in completed.stdout.splitlines() + [""]:
        if not line.strip():
            path = current.get("Path")
            size = current.get("Size", "0")
            folder = current.get("Folder") == "+"
            if path and path != str(archive):
                try:
                    parsed_size = int(size)
                except ValueError:
                    parsed_size = 0
                entries.append((path, parsed_size, folder))
            current = {}
            continue
        if " = " in line:
            key, value = line.split(" = ", 1)
            current[key] = value
    return entries


def scan_archive(archive: Path, settings: Settings, stats: Stats) -> None:
    suffix = unsupported_source_archive_suffix(archive)
    if suffix:
        size = archive.stat().st_size
        stats.add_packed(archive, size, verbose=True)
        print(f"{suffix} is not unpacked by this tool. Extract it with a format-specific tool first.")
        return

    entries = archive_scan_entries(archive)
    if not entries:
        size = archive.stat().st_size
        stats.add_packed(archive, size, verbose=True)
        print("Install p7zip for archive contents scanning, or run with --apply --dst to extract first.")
        return

    for name, size, folder in entries:
        if folder:
            continue
        fake_path = Path(name)
        category = category_for(fake_path, settings)
        if category is None:
            continue
        reason = guard_reason(fake_path, None, settings)
        if reason:
            stats.add_unsafe_skipped(fake_path, reason, verbose=settings.verbose)
            continue
        if category == "packed":
            stats.add_packed(fake_path, size, verbose=settings.verbose)
        else:
            stats.add_candidate(size)
            if settings.verbose:
                print(f"candidate: {human_size(size):>10}  {name}")


def evaluate_source(settings: Settings, source_is_archive: bool) -> tuple[dict[str, object], EvaluationResult]:
    stats = Stats()
    scanned = True
    with StepReporter(settings, "evaluating", detail=settings.source.name):
        source_fingerprint = fingerprint_path(settings.source, settings.hash_mode if settings.manifest else "none")
        if source_is_archive or unsupported_source_archive_suffix(settings.source):
            if process.command_exists("7z"):
                scan_archive(settings.source, settings, stats)
            else:
                scanned = False
        else:
            scan_directory(settings.source, settings, stats)

    source_bytes = int(source_fingerprint.get("bytes", 0) or 0)
    reason = low_value_reason(stats, source_bytes=source_bytes) if scanned else None
    return source_fingerprint, EvaluationResult(
        stats=stats,
        source_bytes=source_bytes,
        scanned=scanned,
        low_value_reason=reason,
    )


def print_evaluation(evaluation: EvaluationResult) -> None:
    stats = evaluation.stats
    rows: list[tuple[str, str | None]] = [
        ("Source size", human_size(evaluation.source_bytes)),
    ]
    if evaluation.scanned:
        rows.append(
            (
                "Candidates",
                f"{count_size_text(stats.candidates, stats.candidate_bytes)} "
                f"({percent_text(stats.candidate_bytes, evaluation.source_bytes)} of source)",
            )
        )
        if stats.packed:
            packed = stats.packed_summary()
            rows.append(("Packed skipped", count_size_text(stats.packed, stats.packed_bytes) + (f" ({packed})" if packed else "")))
        if stats.unsafe_skipped:
            guarded = stats.guarded_summary()
            rows.append(("Guarded skips", f"{stats.unsafe_skipped} files" + (f" ({guarded})" if guarded else "")))
        rows.append(("Value", f"low - {evaluation.low_value_reason}" if evaluation.low_value_reason else "ok"))
    else:
        rows.append(("Contents", "archive scan unavailable; continuing without low-value prompt"))
    print_kv_table("Evaluation", rows)


def confirm_low_value(settings: Settings, evaluation: EvaluationResult) -> bool:
    reason = evaluation.low_value_reason
    if not reason:
        return True
    if settings.low_value == "continue":
        print(f"low-value: continuing ({reason})", flush=True)
        return True
    if settings.low_value == "skip":
        print(f"skip: {reason}", flush=True)
        return False
    if not sys.stdin.isatty():
        print(f"skip: {reason}; non-interactive default is no", flush=True)
        return False
    try:
        answer = input(f"Low-value optimization: {reason}. Continue? [y/N] ")
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer.strip().lower() in {"y", "yes"}


def print_summary(
    stats: Stats,
    *,
    output: Path | None,
    applied: bool,
    source_bytes: int | None = None,
    archive_bytes: int | None = None,
) -> None:
    rows: list[tuple[str, str | None]] = [
        ("Candidates", count_size_text(stats.candidates, stats.candidate_bytes)),
    ]
    if stats.packed:
        packed = stats.packed_summary()
        rows.append(("Packed skipped", count_size_text(stats.packed, stats.packed_bytes) + (f" ({packed})" if packed else "")))
    if stats.unsafe_skipped:
        guarded = stats.guarded_summary()
        rows.append(("Guarded skips", f"{stats.unsafe_skipped} files" + (f" ({guarded})" if guarded else "")))
    if applied:
        saved = max(0, stats.before_bytes - stats.after_bytes)
        rows.extend(
            [
                ("Processed", count_size_text(stats.processed, stats.processed_bytes)),
                ("Resumed", f"{stats.resumed} files" if stats.resumed else None),
                ("Results", f"{stats.optimized} optimized, {stats.skipped} unchanged/skipped, {stats.failed} failed"),
                (
                    "Media savings",
                    f"{human_size(stats.before_bytes)} -> {human_size(stats.after_bytes)}, "
                    f"saved {human_size(saved)} ({save_ratio_text(stats.before_bytes, stats.after_bytes)}, "
                    f"ratio {compression_ratio_text(stats.before_bytes, stats.after_bytes)})",
                ),
                ("Removed", count_size_text(stats.removed, stats.removed_bytes) if stats.removed else None),
                ("Archive", f"{human_size(archive_bytes)} ({percent_text(archive_bytes, source_bytes or 0)} of source)" if archive_bytes is not None else None),
                ("Output", str(output) if output is not None else None),
            ]
        )
        if stats.candidates == 0 and (stats.packed or stats.unsafe_skipped):
            rows.append(("Note", "no loose media was optimized; only extraction/repacking changed size"))
        elif packed_media_dominates(stats):
            rows.append(("Note", "packed containers dominate; loose-media optimization touched only loose files"))
    print_kv_table("Summary", rows)


def default_destination(source: Path) -> Path:
    if source.is_file():
        return source.parent / f"{archive_stem(source)}-optimized"
    return source.with_name(f"{source.name}-optimized")


def prepare_output(settings: Settings) -> Path:
    source = settings.source
    dst = settings.dst or default_destination(source)
    dst = dst.expanduser()
    if source.is_dir() and not settings.in_place:
        ensure_dst_not_inside_src(source, dst)
    ensure_empty_or_missing(dst)
    return dst


def planned_directory_output(settings: Settings) -> Path:
    if settings.in_place:
        return settings.source
    return (settings.dst or default_destination(settings.source)).expanduser()


def skip_existing_directory_if_current(settings: Settings, output: Path, source_fingerprint: dict[str, object]) -> bool:
    if not settings.manifest or settings.force or not output.exists():
        return False
    manifest = read_manifest(manifest_path_for_directory(output))
    if settings.in_place:
        output_fingerprint = fingerprint_path(output, settings.hash_mode)
        if manifest_matches_output(manifest, output_fingerprint, settings):
            print(f"skip: current directory already matches manifest: {output}")
            return True
        return False
    if manifest_matches_source(manifest, source_fingerprint, settings, command="optimize"):
        print(f"skip: optimized directory already exists for this source/settings: {output}")
        return True
    return False


def write_directory_manifest(
    *,
    settings: Settings,
    stats: Stats,
    source_fingerprint: dict[str, object],
    output: Path,
) -> None:
    if not settings.manifest:
        return
    output_fingerprint = fingerprint_path(output, settings.hash_mode)
    manifest = build_manifest(
        command="optimize",
        source=settings.source,
        output=output,
        settings=settings,
        stats=stats,
        source_fingerprint=source_fingerprint,
        output_fingerprint=output_fingerprint,
    )
    write_manifest(manifest_path_for_directory(output), manifest)


def copy_source_tree(source: Path, dst: Path) -> None:
    shutil.copytree(source, dst, symlinks=True, dirs_exist_ok=True)


def copy_payload_to_output(payload: Path, output: Path) -> None:
    shutil.copytree(payload, output, symlinks=True, dirs_exist_ok=True)


def extract_archive_wait(archive: Path, dst: Path, settings: Settings) -> None:
    entries = archive_scan_entries(archive)
    total_files = sum(1 for _, _, folder in entries if not folder) if entries else None
    total_bytes = sum(size for _, size, folder in entries if not folder) if entries else None
    extractor = extract_archive(archive, dst, settings)
    stderr = ""
    with ExtractionReporter(settings, dst, total_files=total_files, total_bytes=total_bytes) as progress:
        while True:
            try:
                _, stderr = extractor.communicate(timeout=0.5)
                break
            except subprocess.TimeoutExpired:
                progress.update()
            except KeyboardInterrupt:
                terminate_process(extractor)
                raise
    if extractor.returncode in {-signal.SIGINT, 130}:
        raise KeyboardInterrupt
    if extractor.returncode != 0:
        if not stderr.strip() and sys.stdin.isatty():
            raise KeyboardInterrupt
        raise ToolError(stderr.strip() or f"extractor failed with status {extractor.returncode}")


def prepare_work_state(
    settings: Settings,
    source_fingerprint: dict[str, object],
    *,
    source_is_archive: bool,
) -> tuple[Path, Path, WorkState]:
    work_root = resolve_work_root(settings, source_fingerprint)
    if settings.clean_work_dir and work_root.exists():
        shutil.rmtree(work_root)
    work_root.mkdir(parents=True, exist_ok=True)
    work_state = WorkState(
        work_root,
        settings,
        source_fingerprint,
        source_is_archive=source_is_archive,
    )
    cleanup_partial_outputs(work_root)
    payload = work_root / WORK_PAYLOAD_NAME
    return work_root, payload, work_state


def stage_source_to_payload(
    settings: Settings,
    source_is_archive: bool,
    payload: Path,
    work_state: WorkState,
    *,
    mode: str,
) -> None:
    if work_state.staged(mode) and payload.exists():
        print(f"resume: using staged payload: {payload}")
        return

    if payload.exists():
        shutil.rmtree(payload)
    payload.mkdir(parents=True, exist_ok=True)

    if source_is_archive:
        extract_archive_wait(settings.source, payload, settings)
    elif mode == "archive-child":
        with StepReporter(settings, "staging", detail=settings.source.name):
            copy_source_as_child(settings.source, payload)
    else:
        with StepReporter(settings, "staging", detail=settings.source.name):
            copy_source_tree(settings.source, payload)
    work_state.mark_staged(mode)


def cleanup_successful_work_dir(settings: Settings, work_root: Path) -> None:
    if settings.keep_work_dir:
        print(f"  work dir kept: {work_root}")
        return
    remove_work_root(work_root)


def remove_work_root(work_root: Path) -> None:
    shutil.rmtree(work_root, ignore_errors=True)
    if work_root.parent.name == WORK_BASE_NAME:
        try:
            work_root.parent.rmdir()
        except OSError:
            pass


def confirm_remove_work_dir(work_root: Path) -> bool:
    if not sys.stdin.isatty():
        return False
    try:
        answer = input(f"Remove resumable work dir {work_root}? [y/N] ")
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer.strip().lower() in {"y", "yes"}


def handle_interrupted_work_dir(work_root: Path) -> None:
    print("\ninterrupted.", file=sys.stderr)
    if not work_root.exists():
        return
    if confirm_remove_work_dir(work_root):
        remove_work_root(work_root)
        print(f"removed work dir: {work_root}", file=sys.stderr)
    else:
        print(f"kept resumable work dir: {work_root}", file=sys.stderr)


def validate_apply_dependencies(settings: Settings, source_is_archive: bool) -> None:
    missing: list[str] = []
    if not settings.skip_images and not process.command_exists("magick"):
        missing.append("imagemagick")
    if (not settings.skip_audio or not settings.skip_video) and not process.command_exists("ffmpeg"):
        missing.append("ffmpeg")
    if source_is_archive:
        try:
            find_extractor(settings.source, settings.extract_jobs)
        except ToolError as exc:
            raise ToolError(str(exc)) from exc
    if missing:
        raise ToolError("missing required package/command: " + ", ".join(missing))


def validate_repack_dependencies(settings: Settings, source_is_archive: bool) -> None:
    validate_apply_dependencies(settings, source_is_archive)
    if settings.archive_format == "tar.zst":
        process.require("tar", "zstd")
    elif settings.archive_format == "7z":
        process.require("7z")
    else:
        raise ToolError(f"unsupported archive format: {settings.archive_format}")


def print_plan(settings: Settings, source_is_archive: bool) -> None:
    mode = "in-place" if settings.in_place else settings.command
    rows: list[tuple[str, str | None]] = [
        ("Mode", mode),
        ("Source", str(settings.source)),
    ]
    if mode == "optimize":
        destination = str(planned_directory_output(settings))
        if not settings.dst:
            destination += " (source sibling)"
        rows.append(("Destination", destination))
    elif mode in {"repack", "pack"}:
        destination = str(resolve_archive_output(settings))
        if not settings.dst and not settings.output_archive:
            destination += " (source sibling)"
        rows.append(("Destination", destination))
    elif settings.dst:
        rows.append(("Destination", str(settings.dst)))
    rows.extend(
        [
            ("Media", f"{settings.max_size}, {settings.engine_policy} policy"),
            ("Workers", f"{settings.jobs} optimize, {settings.video_jobs} video, {settings.extract_jobs} extract"),
        ]
    )
    if not settings.skip_video:
        encoder = selected_video_encoder(settings)
        rows.append(("Video encoder", encoder))
    if mode in {"repack", "pack"}:
        archive = settings.archive_format
        if settings.archive_format == "tar.zst":
            archive += f", zstd {settings.zstd_level}"
        rows.append(("Archive", archive))
    if source_is_archive and settings.apply:
        rows.append(("Pipeline", "staged, resumable"))
    if settings.apply and not settings.in_place:
        work_label = str(settings.work_dir) if settings.work_dir else str(settings.source.parent / WORK_BASE_NAME)
        rows.extend(
            [
                ("Work dir", work_label),
                ("Resume", "yes" if settings.resume else "no"),
                ("Progress", settings.progress),
                ("Low value", settings.low_value),
            ]
        )
    print_kv_table("VN asset optimizer", rows)


def add_source_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("source_arg", nargs="?", help="source directory or compressed archive")
    parser.add_argument("--src", dest="source_opt", help="source directory or compressed archive")


def add_common_optimizer_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--profile", choices=sorted(PROFILES), default="phone-fhd", help="quality/size preset")
    parser.add_argument("--max", "--max-size", dest="max_size", type=parse_geometry, help="max image/video bounds")
    parser.add_argument("--jpeg-quality", type=parse_quality, help="JPEG quality, 1-100")
    parser.add_argument("--webp-quality", type=parse_quality, help="WebP quality, 1-100")
    parser.add_argument("--ogg-quality", type=int, help="libvorbis quality, usually 0-10")
    parser.add_argument("--mp3-bitrate", help="MP3/AAC/Opus audio bitrate, for example 128k")
    parser.add_argument("--video-crf", type=int, help="H.264 CRF; lower is larger/better")
    parser.add_argument("--webm-crf", type=int, help="VP9 CRF for .webm; lower is larger/better")
    parser.add_argument(
        "--video-encoder",
        choices=("auto", "x264", "nvenc"),
        default="auto",
        help="H.264 encoder for mp4/mov files; auto uses NVENC when available",
    )
    parser.add_argument("--video-preset", default="veryfast", help="libx264 preset; default: veryfast")
    parser.add_argument("--nvenc-preset", default="p5", help="NVENC preset; default: p5")
    parser.add_argument("--ffmpeg-threads", type=parse_positive_int, default=2, help="threads per CPU ffmpeg job")
    parser.add_argument("--magick-threads", type=parse_positive_int, default=1, help="threads per ImageMagick job")
    parser.add_argument("--jobs", type=parse_positive_int, default=-1, help="parallel optimization jobs; default: auto, up to 8")
    parser.add_argument("--video-jobs", type=parse_positive_int, default=-1, help="parallel video encodes; default: auto")
    parser.add_argument("--extract-jobs", type=parse_positive_int, default=-1, help="extractor/7z threads; default: auto")
    parser.add_argument(
        "--stable-seconds",
        type=parse_nonnegative_float,
        default=2.0,
        help="legacy pipeline wait setting; ignored by resumable staged runs",
    )
    parser.add_argument(
        "--engine-policy",
        choices=("safe", "balanced", "aggressive"),
        default="balanced",
        help="engine guardrail strictness; default: balanced",
    )
    parser.add_argument(
        "--hash-mode",
        choices=("auto", "none", "partial", "full"),
        default="auto",
        help="manifest hash mode; default: auto",
    )
    parser.add_argument("--manifest", action=argparse.BooleanOptionalAction, default=True, help="write/read manifests")
    parser.add_argument("--skip-images", action="store_true", help="do not optimize image files")
    parser.add_argument("--skip-audio", action="store_true", help="do not optimize audio files")
    parser.add_argument("--skip-video", action="store_true", help="do not optimize video files")
    parser.add_argument(
        "--strip-pc-runtime",
        action="store_true",
        help="remove common Ren'Py desktop launchers/runtime dirs from the output copy",
    )
    parser.add_argument("--strip-cache", action="store_true", help="remove game/cache directories from the output copy")
    parser.add_argument("--verbose", "-v", action="store_true", help="list scan candidates and packed files")


def add_extract_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--extract",
        choices=("auto", "yes", "no"),
        default="auto",
        help="extract archive sources before optimizing; default: auto",
    )
    parser.add_argument(
        "--pipeline",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="legacy option; resumable runs stage first so progress totals are exact",
    )
    parser.add_argument("--work-dir", help="temporary working directory for extraction/copy")
    parser.add_argument("--keep-work-dir", action="store_true", help="keep work directory after successful completion")
    parser.add_argument("--clean-work-dir", action="store_true", help="discard existing resumable work state before starting")
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="reuse completed workdir files from prior interrupted runs; default: enabled",
    )
    parser.add_argument(
        "--progress",
        choices=("auto", "rich", "plain", "off"),
        default="auto",
        help="progress display; default: auto",
    )
    parser.add_argument(
        "--low-value",
        choices=("ask", "skip", "continue"),
        default="ask",
        help="action when preflight finds little/no optimizable media; default: ask in a TTY, skip otherwise",
    )
    parser.add_argument(
        "--skip-low-value",
        dest="low_value",
        action="store_const",
        const="skip",
        help="skip automatically when preflight finds little/no optimizable media",
    )
    parser.add_argument(
        "--continue-low-value",
        dest="low_value",
        action="store_const",
        const="continue",
        help="continue automatically when preflight finds little/no optimizable media",
    )


def add_archive_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--archive-format",
        choices=("tar.zst", "7z"),
        default=DEFAULT_ARCHIVE_FORMAT,
        help=f"output archive format; default: {DEFAULT_ARCHIVE_FORMAT}",
    )
    parser.add_argument("--output-archive", help="explicit output archive path")
    parser.add_argument(
        "--zstd-level",
        type=parse_zstd_level,
        default=DEFAULT_ZSTD_LEVEL,
        help=f"zstd compression level 1-19; default: {DEFAULT_ZSTD_LEVEL}",
    )
    parser.add_argument(
        "--zstd-long",
        type=parse_optional_int,
        default=None,
        help="enable zstd long mode with a window log, or 'off'; default: off",
    )
    parser.add_argument("--7z-level", dest="sevenzip_level", type=parse_7z_level, default=7, help="7z level; default: 7")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vn-optimize-assets",
        description="Optimize unpacked VN assets or extract/repack archives into Android/JoiPlay-sized copies.",
    )
    subcommands = parser.add_subparsers(dest="command")

    scan = subcommands.add_parser("scan", help="scan source and report optimizable assets without writing")
    add_source_arg(scan)
    add_common_optimizer_args(scan)

    optimize = subcommands.add_parser("optimize", help="write an optimized directory copy or optimize in place")
    add_source_arg(optimize)
    optimize.add_argument("--dst", help="destination directory for optimized copy")
    optimize.add_argument("--apply", action="store_true", help=argparse.SUPPRESS)
    optimize.add_argument("--in-place", action="store_true", help="optimize SOURCE directly; use only on a disposable copy")
    optimize.add_argument("--force", action="store_true", help="ignore matching manifests and overwrite existing outputs")
    add_extract_args(optimize)
    add_common_optimizer_args(optimize)

    repack = subcommands.add_parser(
        "repack",
        aliases=("pack",),
        help="optimize a source directory/archive and write an optimized compressed archive",
    )
    add_source_arg(repack)
    repack.add_argument("--dst", help="destination directory or explicit archive path")
    repack.add_argument("--force", action="store_true", help="ignore matching manifests and overwrite existing archive")
    add_extract_args(repack)
    add_archive_args(repack)
    add_common_optimizer_args(repack)
    return parser


def normalize_legacy_argv(argv: list[str]) -> list[str]:
    if not argv:
        return argv
    if argv[0] in {"-h", "--help"}:
        return argv
    commands = {"scan", "optimize", "repack", "pack"}
    for arg in argv:
        if arg == "--":
            break
        if arg.startswith("-"):
            continue
        if arg in commands:
            return argv
        command = "optimize" if ("--apply" in argv or "--in-place" in argv) else "scan"
        return [command, *argv]
    return argv


def settings_from_args(args: argparse.Namespace) -> Settings:
    source_text = args.source_opt or args.source_arg
    if args.source_opt and args.source_arg:
        raise ToolError("provide source either positionally or with --src, not both")
    if not source_text:
        raise ToolError("missing source path")

    source = Path(source_text).expanduser()
    if not source.exists():
        raise ToolError(f"source not found: {source}")
    source = source.resolve()

    if getattr(args, "apply", False) and getattr(args, "in_place", False):
        raise ToolError("--apply and --in-place are mutually exclusive")

    profile = PROFILES[args.profile]
    video_encoder = args.video_encoder
    video_jobs = auto_video_jobs("nvenc" if video_encoder == "auto" and process.command_exists("nvidia-smi") else video_encoder)
    if args.video_jobs != -1:
        video_jobs = args.video_jobs

    command = "repack" if args.command == "pack" else args.command

    return Settings(
        command=command,
        source=source,
        dst=Path(args.dst).expanduser() if getattr(args, "dst", None) else None,
        apply=args.command in {"optimize", "repack", "pack"},
        in_place=bool(getattr(args, "in_place", False)),
        force=bool(getattr(args, "force", False)),
        extract=getattr(args, "extract", "auto"),
        pipeline=bool(getattr(args, "pipeline", True)),
        work_dir=Path(args.work_dir).expanduser() if getattr(args, "work_dir", None) else None,
        keep_work_dir=bool(getattr(args, "keep_work_dir", False)),
        clean_work_dir=bool(getattr(args, "clean_work_dir", False)),
        resume=bool(getattr(args, "resume", True)),
        progress=getattr(args, "progress", "auto"),
        low_value=getattr(args, "low_value", "ask"),
        jobs=auto_jobs() if args.jobs == -1 else args.jobs,
        video_jobs=video_jobs,
        extract_jobs=auto_extract_jobs() if args.extract_jobs == -1 else args.extract_jobs,
        stable_seconds=args.stable_seconds,
        engine_policy=args.engine_policy,
        manifest=bool(args.manifest),
        hash_mode=args.hash_mode,
        max_size=args.max_size or profile.max_size,
        jpeg_quality=args.jpeg_quality or profile.jpeg_quality,
        webp_quality=args.webp_quality or profile.webp_quality,
        ogg_quality=args.ogg_quality if args.ogg_quality is not None else profile.ogg_quality,
        mp3_bitrate=args.mp3_bitrate or profile.mp3_bitrate,
        video_crf=args.video_crf if args.video_crf is not None else profile.video_crf,
        webm_crf=args.webm_crf if args.webm_crf is not None else profile.webm_crf,
        video_encoder=video_encoder,
        video_preset=args.video_preset,
        nvenc_preset=args.nvenc_preset,
        ffmpeg_threads=args.ffmpeg_threads,
        magick_threads=args.magick_threads,
        skip_images=args.skip_images,
        skip_audio=args.skip_audio,
        skip_video=args.skip_video,
        strip_pc_runtime=args.strip_pc_runtime,
        strip_cache=args.strip_cache,
        archive_format=getattr(args, "archive_format", DEFAULT_ARCHIVE_FORMAT),
        output_archive=Path(args.output_archive).expanduser() if getattr(args, "output_archive", None) else None,
        zstd_level=getattr(args, "zstd_level", DEFAULT_ZSTD_LEVEL),
        zstd_long=getattr(args, "zstd_long", None),
        sevenzip_level=getattr(args, "sevenzip_level", 7),
        verbose=args.verbose,
    )


def run_scan(settings: Settings, stats: Stats, source_is_archive: bool) -> None:
    if source_is_archive or unsupported_source_archive_suffix(settings.source):
        scan_archive(settings.source, settings, stats)
    else:
        scan_directory(settings.source, settings, stats)
    print_summary(stats, output=None, applied=False)


def run_apply(settings: Settings, stats: Stats, source_is_archive: bool) -> None:
    source_fingerprint, evaluation = evaluate_source(settings, source_is_archive)
    planned_output = planned_directory_output(settings)
    if skip_existing_directory_if_current(settings, planned_output, source_fingerprint):
        return
    print_evaluation(evaluation)
    if not confirm_low_value(settings, evaluation):
        return
    validate_apply_dependencies(settings, source_is_archive)

    if settings.in_place:
        if source_is_archive:
            raise ToolError("--in-place cannot be used with archive sources")
        run_parallel(settings.source, settings, stats)
        strip_android_extras(settings.source, settings, stats)
        write_directory_manifest(
            settings=settings,
            stats=stats,
            source_fingerprint=source_fingerprint,
            output=settings.source,
        )
        print_summary(stats, output=settings.source, applied=True)
        return

    output = prepare_output(settings)
    work_root, payload, work_state = prepare_work_state(
        settings,
        source_fingerprint,
        source_is_archive=source_is_archive,
    )
    try:
        stage_source_to_payload(
            settings,
            source_is_archive,
            payload,
            work_state,
            mode="contents",
        )
        run_parallel(payload, settings, stats, work_state)
        strip_android_extras(payload, settings, stats)
        if stats.failed:
            print_summary(stats, output=payload, applied=True)
            raise ToolError(f"optimization failed; resumable work dir kept: {work_root}")
        ensure_empty_or_missing(output)
        with StepReporter(settings, "publishing", detail=output.name):
            copy_payload_to_output(payload, output)
        write_directory_manifest(
            settings=settings,
            stats=stats,
            source_fingerprint=source_fingerprint,
            output=output,
        )
        print_summary(stats, output=output, applied=True)
        cleanup_successful_work_dir(settings, work_root)
    except KeyboardInterrupt:
        handle_interrupted_work_dir(work_root)
        raise SystemExit(130) from None


def write_repack_manifests(
    *,
    settings: Settings,
    stats: Stats,
    source_fingerprint: dict[str, object],
    work_root: Path,
    archive: Path,
) -> None:
    if not settings.manifest:
        return
    work_fingerprint = fingerprint_path(work_root, settings.hash_mode)
    archive_fingerprint = fingerprint_path(archive, settings.hash_mode)
    repack_manifest = build_manifest(
        command="repack",
        source=settings.source,
        output=archive,
        archive=archive,
        settings=settings,
        stats=stats,
        source_fingerprint=source_fingerprint,
        output_fingerprint=archive_fingerprint,
        archive_fingerprint=archive_fingerprint,
    )
    repack_manifest["optimized_tree_fingerprint"] = work_fingerprint
    write_manifest(manifest_path_for_archive(archive), repack_manifest)


def optimize_payload(settings: Settings, stats: Stats, payload: Path, work_state: WorkState) -> Path:
    run_parallel(payload, settings, stats, work_state)
    strip_android_extras(payload, settings, stats)
    return payload


def run_repack(settings: Settings, stats: Stats, source_is_archive: bool) -> None:
    source_fingerprint, evaluation = evaluate_source(settings, source_is_archive)
    archive = resolve_archive_output(settings)
    if skip_existing_archive_if_current(settings, archive, source_fingerprint):
        return
    if archive.exists() and not settings.force:
        raise ToolError(f"archive already exists: {archive}")
    print_evaluation(evaluation)
    if not confirm_low_value(settings, evaluation):
        return
    validate_repack_dependencies(settings, source_is_archive)

    work_root, payload, work_state = prepare_work_state(
        settings,
        source_fingerprint,
        source_is_archive=source_is_archive,
    )
    try:
        stage_source_to_payload(
            settings,
            source_is_archive,
            payload,
            work_state,
            mode="contents" if source_is_archive else "archive-child",
        )
        optimized_root = optimize_payload(settings, stats, payload, work_state)
        if stats.failed:
            print_summary(stats, output=optimized_root, applied=True)
            raise ToolError(f"optimization failed; resumable work dir kept: {work_root}")
        if settings.manifest:
            tree_fingerprint = fingerprint_path(optimized_root, settings.hash_mode)
            tree_manifest = build_manifest(
                command="optimize",
                source=settings.source,
                output=optimized_root,
                settings=settings,
                stats=stats,
                source_fingerprint=source_fingerprint,
                output_fingerprint=tree_fingerprint,
            )
            write_manifest(manifest_path_for_directory(optimized_root), tree_manifest)
        create_archive(optimized_root, archive, settings)
        write_repack_manifests(
            settings=settings,
            stats=stats,
            source_fingerprint=source_fingerprint,
            work_root=optimized_root,
            archive=archive,
        )
        before_bytes = int(source_fingerprint.get("bytes", 0) or tree_size(settings.source))
        archive_bytes = archive.stat().st_size
        print_summary(stats, output=archive, applied=True, source_bytes=before_bytes, archive_bytes=archive_bytes)
        cleanup_successful_work_dir(settings, work_root)
    except KeyboardInterrupt:
        handle_interrupted_work_dir(work_root)
        raise SystemExit(130) from None


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(normalize_legacy_argv(raw_argv))
    settings = settings_from_args(args)
    source_is_archive = is_extractable_archive(settings.source)
    unsupported_suffix = unsupported_source_archive_suffix(settings.source)

    if settings.source.is_file() and not source_is_archive and not unsupported_suffix:
        raise ToolError(f"source file is not a supported archive: {settings.source}")
    if unsupported_suffix and settings.command != "scan":
        raise ToolError(f"{unsupported_suffix} sources are not extractable by this tool")
    if settings.extract == "yes" and not source_is_archive:
        raise ToolError("--extract yes requires an archive source")
    if settings.extract == "no" and source_is_archive and settings.command in {"optimize", "repack"}:
        raise ToolError("archive source needs extraction; omit --extract no")

    print_plan(settings, source_is_archive)
    stats = Stats()
    try:
        if settings.command == "repack":
            run_repack(settings, stats, source_is_archive)
        elif settings.command == "optimize":
            run_apply(settings, stats, source_is_archive)
        elif settings.command == "scan":
            run_scan(settings, stats, source_is_archive)
        else:
            raise ToolError(f"unknown command: {settings.command}")
    except KeyboardInterrupt:
        print("\ninterrupted.", file=sys.stderr)
        return 130

    return 1 if stats.failed else 0
