"""Free desktop resources before launching a game."""

from __future__ import annotations

import argparse
import os
import re
import shlex
import signal
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import notify, process
from .cli import add_dry_run
from .paths import xdg_cache_home


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    comm: str
    cmdline: str


@dataclass(frozen=True)
class ProcessTarget:
    label: str
    comm_names: tuple[str, ...]
    cmdline_patterns: tuple[re.Pattern[str], ...]


def _patterns(*patterns: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)


APP_TARGETS = (
    ProcessTarget(
        "Slack",
        ("slack",),
        _patterns(r"(^|\s|/)slack(\s|$)"),
    ),
    ProcessTarget(
        "LM Studio",
        ("lm-studio", "lmstudio", "LM Studio"),
        _patterns(r"(^|\s|/)(lm-studio|lmstudio|LM Studio)(\s|$)"),
    ),
    ProcessTarget(
        "OpenWhispr",
        ("openwhispr", "open-whispr", "open-whispr-app"),
        _patterns(r"(^|\s|/)(openwhispr|open-whispr|open-whispr-app)(\s|$)"),
    ),
    ProcessTarget(
        "Neovim",
        ("nvim",),
        _patterns(r"(^|\s|/)nvim(\s|$)"),
    ),
)

OPTIMIZATION_TARGETS = (
    ProcessTarget(
        "desktop search indexers",
        (
            "baloo_file",
            "baloo_file_extractor",
            "tracker-miner-fs",
            "tracker-miner-fs-3",
            "tracker-extract",
            "tracker-extract-3",
            "tracker-store",
        ),
        _patterns(
            r"(^|\s|/)baloo_file(\s|$)",
            r"(^|\s|/)baloo_file_extractor(\s|$)",
            r"(^|\s|/)tracker-miner-fs(-3)?(\s|$)",
            r"(^|\s|/)tracker-extract(-3)?(\s|$)",
            r"(^|\s|/)tracker-store(\s|$)",
        ),
    ),
    ProcessTarget(
        "background database builders",
        ("updatedb", "plocate-build", "mandb"),
        _patterns(
            r"(^|\s|/)updatedb(\s|$)",
            r"(^|\s|/)plocate-build(\s|$)",
            r"(^|\s|/)mandb(\s|$)",
        ),
    ),
)

INDEXER_SERVICES = (
    "tracker-miner-fs-3.service",
    "tracker-extract-3.service",
    "tracker-miner-fs.service",
    "tracker-extract.service",
    "baloo.service",
)


class GamePrep:
    def __init__(
        self,
        *,
        dry_run: bool = False,
        grace_seconds: float = 3,
        force: bool = True,
        optimize: bool = True,
        unload_models: bool = True,
    ) -> None:
        self.dry_run = dry_run
        self.grace_seconds = grace_seconds
        self.force = force
        self.optimize = optimize
        self.unload_models = unload_models
        self.title = "Game prep"
        self.log_dir = xdg_cache_home() / "game-prep"
        self.log_file = self.log_dir / "prep.log"

    def setup_log(self) -> None:
        if self.dry_run:
            print(f"+ truncate {self.log_file}")
            return
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.write_text("", encoding="utf-8")

    def log(self, message: str) -> None:
        line = f"[{datetime.now():%F %T}] [INFO] {message}"
        if self.dry_run:
            print(line)
            return
        with self.log_file.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def notify(self, message: str, urgency: str = "normal") -> None:
        notify.notify(self.title, message, urgency=urgency, dry_run=self.dry_run)

    def run_optional(self, label: str, command: list[str], *, log_failure: bool = True) -> bool:
        if not process.command_exists(command[0]):
            self.log(f"Skipped {label}: missing command '{command[0]}'.")
            return False
        self.log(f"Running {label}: {process.printable(command)}")
        completed = process.run(command, dry_run=self.dry_run, log_file=self.log_file)
        if completed.returncode != 0 and log_failure:
            self.log(f"{label} exited with status {completed.returncode}.")
        return completed.returncode == 0

    def unload_lm_studio_models(self) -> None:
        if not process.command_exists("lms"):
            self.log("Skipped LM Studio model unload: missing command 'lms'.")
            return
        self.run_optional("LM Studio model unload", ["lms", "unload", "--all"], log_failure=True)

    def unload_openwhispr_models(self) -> None:
        command_text = os.environ.get("OPENWHISPR_UNLOAD_CMD", "").strip()
        if not command_text:
            self.log("OpenWhispr has no known external unload command; closing it releases its loaded model.")
            return
        try:
            command = shlex.split(command_text)
        except ValueError as exc:
            self.log(f"Skipped OpenWhispr model unload: invalid OPENWHISPR_UNLOAD_CMD: {exc}.")
            return
        if command:
            self.run_optional("OpenWhispr model unload", command, log_failure=True)

    def unload_ai_models(self) -> None:
        if not self.unload_models:
            self.log("Skipping model unloads by request.")
            return
        self.unload_lm_studio_models()
        self.unload_openwhispr_models()

    def stop_indexer_services(self) -> None:
        if not process.command_exists("systemctl"):
            self.log("Skipped user service stops: missing command 'systemctl'.")
            return
        for service in INDEXER_SERVICES:
            if self.dry_run:
                print(f"+ systemctl --user stop {service}")
                continue
            active = process.run(["systemctl", "--user", "is-active", "--quiet", service], quiet=True)
            if active.returncode != 0:
                self.log(f"Skipped inactive user service: {service}.")
                continue
            self.run_optional(f"stop {service}", ["systemctl", "--user", "stop", service], log_failure=True)

    def sync_filesystems(self) -> None:
        self.run_optional("filesystem sync", ["sync"], log_failure=False)

    def optimize_lightly(self) -> None:
        if not self.optimize:
            self.log("Skipping optimization commands by request.")
            return
        self.stop_indexer_services()
        self.terminate_targets(OPTIMIZATION_TARGETS, grace_seconds=1, force=False)
        self.sync_filesystems()

    def terminate_targets(
        self,
        targets: tuple[ProcessTarget, ...],
        *,
        grace_seconds: float,
        force: bool,
    ) -> int:
        total = 0
        for target in targets:
            matches = self.matching_processes(target)
            if not matches:
                self.log(f"No {target.label} processes found.")
                continue
            total += len(matches)
            self.log(f"Stopping {len(matches)} {target.label} process(es).")
            self.signal_processes(target.label, matches, signal.SIGTERM)

        if total == 0:
            return 0

        if not self.dry_run and grace_seconds > 0:
            time.sleep(grace_seconds)

        if force:
            for target in targets:
                remaining = self.matching_processes(target)
                if remaining:
                    self.log(f"Force killing {len(remaining)} remaining {target.label} process(es).")
                    self.signal_processes(target.label, remaining, signal.SIGKILL)
        return total

    def matching_processes(self, target: ProcessTarget) -> list[ProcessInfo]:
        current_pid = os.getpid()
        comm_names = {name.lower() for name in target.comm_names}
        matches: list[ProcessInfo] = []
        for proc in self.user_processes():
            if proc.pid == current_pid:
                continue
            if proc.comm.lower() in comm_names or any(pattern.search(proc.cmdline) for pattern in target.cmdline_patterns):
                matches.append(proc)
        return matches

    def signal_processes(self, label: str, processes: list[ProcessInfo], sig: signal.Signals) -> None:
        signal_name = sig.name.removeprefix("SIG")
        for proc in processes:
            detail = f"{proc.pid} ({proc.comm})"
            if self.dry_run:
                print(f"+ kill -{signal_name} {proc.pid} # {label}: {proc.comm}")
                continue
            try:
                os.kill(proc.pid, sig)
                self.log(f"Sent {signal_name} to {label}: {detail}.")
            except ProcessLookupError:
                self.log(f"{label} already exited: {detail}.")
            except PermissionError:
                self.log(f"Permission denied sending {signal_name} to {label}: {detail}.")

    def user_processes(self) -> list[ProcessInfo]:
        proc_root = Path("/proc")
        uid = os.getuid()
        processes: list[ProcessInfo] = []
        for entry in proc_root.iterdir():
            if not entry.name.isdigit():
                continue
            pid = int(entry.name)
            try:
                if self.process_uid(entry) != uid:
                    continue
                comm = (entry / "comm").read_text(encoding="utf-8", errors="replace").strip()
                raw_cmdline = (entry / "cmdline").read_bytes()
            except (FileNotFoundError, ProcessLookupError, PermissionError, OSError):
                continue
            parts = [part.decode("utf-8", errors="replace") for part in raw_cmdline.split(b"\0") if part]
            cmdline = " ".join(parts) if parts else comm
            processes.append(ProcessInfo(pid=pid, comm=comm, cmdline=cmdline))
        return processes

    @staticmethod
    def process_uid(proc_path: Path) -> int | None:
        try:
            for line in (proc_path / "status").read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("Uid:"):
                    return int(line.split()[1])
        except (FileNotFoundError, ProcessLookupError, PermissionError, OSError, ValueError):
            return None
        return None

    def run(self) -> int:
        self.setup_log()
        self.unload_ai_models()
        stopped_apps = self.terminate_targets(APP_TARGETS, grace_seconds=self.grace_seconds, force=self.force)
        self.optimize_lightly()
        self.notify(f"Stopped {stopped_apps} game-distraction process(es).")
        self.log("Game prep complete.")
        return 0


def _positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="game-prep",
        description="Stop AI/chat/editor background work before launching a game.",
    )
    add_dry_run(parser)
    parser.add_argument(
        "--grace-seconds",
        type=_positive_float,
        default=3.0,
        help="seconds to wait after SIGTERM before force killing app targets",
    )
    parser.add_argument("--no-force", action="store_true", help="do not send SIGKILL after the grace period")
    parser.add_argument("--no-optimize", action="store_true", help="skip light indexer stops and filesystem sync")
    parser.add_argument("--skip-model-unload", action="store_true", help="skip LM Studio/OpenWhispr unload attempts")
    args = parser.parse_args(argv)

    return GamePrep(
        dry_run=args.dry_run,
        grace_seconds=args.grace_seconds,
        force=not args.no_force,
        optimize=not args.no_optimize,
        unload_models=not args.skip_model_unload,
    ).run()
