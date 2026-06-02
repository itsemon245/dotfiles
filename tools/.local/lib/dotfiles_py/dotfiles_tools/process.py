"""Subprocess helpers with dry-run and optional logging support."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, Sequence

from .cli import ToolError


Command = Sequence[str | os.PathLike[str]]


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def which(command: str) -> str | None:
    return shutil.which(command)


def require(*commands: str) -> None:
    missing = [command for command in commands if not command_exists(command)]
    if missing:
        raise ToolError("missing required command: " + ", ".join(missing))


def printable(command: Command) -> str:
    return " ".join(shlex.quote(str(part)) for part in command)


def run(
    command: Command,
    *,
    check: bool = False,
    capture: bool = False,
    dry_run: bool = False,
    env: dict[str, str] | None = None,
    cwd: str | Path | None = None,
    input_bytes: bytes | None = None,
    log_file: str | Path | None = None,
    quiet: bool = False,
) -> subprocess.CompletedProcess:
    if dry_run:
        print("+ " + printable(command))
        return subprocess.CompletedProcess(list(map(str, command)), 0, "", "")

    kwargs = {
        "check": check,
        "env": env,
        "cwd": cwd,
    }

    if input_bytes is not None:
        kwargs["input"] = input_bytes

    if capture:
        kwargs.update({"stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "text": True})
    elif quiet and log_file is None:
        kwargs.update({"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL})

    if log_file is not None:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        with Path(log_file).open("ab") as handle:
            return subprocess.run(
                [str(part) for part in command],
                stdout=handle,
                stderr=subprocess.STDOUT,
                **kwargs,
            )

    return subprocess.run([str(part) for part in command], **kwargs)


def output(command: Command, *, env: dict[str, str] | None = None) -> str:
    completed = run(command, capture=True, env=env)
    if completed.returncode != 0:
        return ""
    return completed.stdout


def background(
    command: Command,
    *,
    dry_run: bool = False,
    env: dict[str, str] | None = None,
    log_file: str | Path | None = None,
) -> subprocess.Popen | None:
    if dry_run:
        print("+ " + printable(command) + " &")
        return None

    stdout = subprocess.DEVNULL
    stderr = subprocess.DEVNULL
    handle = None
    if log_file is not None:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handle = Path(log_file).open("ab")
        stdout = handle
        stderr = subprocess.STDOUT

    return subprocess.Popen(
        [str(part) for part in command],
        env=env,
        stdout=stdout,
        stderr=stderr,
        start_new_session=True,
    )


def pgrep(*args: str) -> bool:
    if not command_exists("pgrep"):
        return False
    return subprocess.run(["pgrep", *args], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def pkill(*args: str, dry_run: bool = False) -> bool:
    if not command_exists("pkill"):
        return False
    return run(["pkill", *args], dry_run=dry_run).returncode == 0


def command_lines(command: Command) -> list[str]:
    text = output(command)
    return [line for line in text.splitlines() if line]


def stream_pipeline(commands: Iterable[Command]) -> int:
    processes: list[subprocess.Popen] = []
    previous = None
    for command in commands:
        process = subprocess.Popen(
            [str(part) for part in command],
            stdin=previous.stdout if previous else None,
            stdout=subprocess.PIPE,
        )
        if previous and previous.stdout:
            previous.stdout.close()
        processes.append(process)
        previous = process

    if previous and previous.stdout:
        previous.communicate()
    status = 0
    for process in processes:
        process.wait()
        status = process.returncode if process.returncode else status
    return status
