"""Path checks and removal for sysclean.

Everything that deletes goes through this module. It takes paths from declared
rules, never from a search, and it never uses a shell.
"""

from __future__ import annotations

import os
import pwd
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .cli import ToolError

# A target may not contain these, because removing it would remove them too.
KEEP = (
    ".ssh",
    ".gnupg",
    ".config",
    ".local",
    ".local/share",
    ".mozilla",
    "dotfiles",
    "Documents",
    "Downloads",
    "Pictures",
    "Projects",
    "Work",
)
# A target may not be inside these at all.
NEVER_INSIDE = (
    ".ssh",
    ".gnupg",
    ".mozilla",
    ".local/share/Steam",
    ".local/share/Trash",
    "dotfiles",
)


@dataclass(frozen=True)
class Usage:
    size: int
    files: int
    newest: float


def real_home() -> Path:
    """The running user's home from the password database, not from $HOME."""
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


def check_base(base: Path) -> Path:
    """Allow only the real home, or a throwaway directory for tests."""
    resolved = Path(os.path.realpath(base))
    allowed = resolved == Path(os.path.realpath(real_home()))
    allowed = allowed or resolved.is_relative_to(os.path.realpath(tempfile.gettempdir()))
    if not allowed or resolved == Path(os.path.realpath(tempfile.gettempdir())):
        raise ToolError(f"refusing unexpected base directory: {base}")
    return resolved


def check_target(base: Path, relative: str) -> tuple[Path | None, str | None]:
    """Return the checked absolute path, or the reason it may not be touched."""
    parts = relative.split("/")
    if not relative or relative.startswith("/") or any(part in ("", ".", "..") for part in parts):
        return None, "invalid path"
    for name in KEEP:
        if name == relative or name.startswith(relative + "/"):
            return None, f"would remove protected path {name}"
    for name in NEVER_INSIDE:
        if relative == name or relative.startswith(name + "/"):
            return None, f"inside protected path {name}"
    path = base / relative
    if not os.path.lexists(path):
        return None, "missing"
    if os.path.realpath(path) != str(path):
        return None, f"resolves to {os.path.realpath(path)}"
    if not stat.S_ISDIR(os.lstat(path).st_mode):
        return None, "not a directory"
    return path, None


def measure(path: Path) -> Usage:
    """Measure without following links. Raises ToolError if a mount is inside."""
    info = os.lstat(path)
    size, files, newest = info.st_blocks * 512, 0, info.st_mtime
    if not stat.S_ISDIR(info.st_mode):
        return Usage(size, 1, newest)
    for current, directories, names in os.walk(path, followlinks=False):
        for name in directories + names:
            entry = os.lstat(os.path.join(current, name))
            if entry.st_dev != info.st_dev:
                raise ToolError(f"different filesystem inside target: {current}/{name}")
            size += entry.st_blocks * 512
            newest = max(newest, entry.st_mtime)
            files += 0 if stat.S_ISDIR(entry.st_mode) else 1
    return Usage(size, files, newest)


def _process_paths(pid: str) -> list[str]:
    paths: list[str] = []
    for name in ("cwd", "exe"):
        try:
            paths.append(os.readlink(f"/proc/{pid}/{name}"))
        except OSError:
            pass
    try:
        for descriptor in os.listdir(f"/proc/{pid}/fd"):
            try:
                paths.append(os.readlink(f"/proc/{pid}/fd/{descriptor}"))
            except OSError:
                pass
        with open(f"/proc/{pid}/maps", errors="replace") as handle:
            paths.extend(line.split(None, 5)[5].strip() for line in handle if len(line.split(None, 5)) == 6)
    except OSError:
        pass
    return paths


def users_of(paths: list[Path]) -> dict[Path, set[str]]:
    """Find processes with a cwd, exe, open file, or mapped file inside the paths."""
    prefixes = {str(path) + "/": path for path in paths}
    users: dict[Path, set[str]] = {}
    for pid in filter(str.isdigit, os.listdir("/proc")):
        for seen in _process_paths(pid):
            for prefix, path in prefixes.items():
                if seen.startswith(prefix) or seen + "/" == prefix:
                    try:
                        name = Path(f"/proc/{pid}/comm").read_text().strip()
                    except OSError:
                        name = "unknown"
                    users.setdefault(path, set()).add(name)
    return users


def running_commands() -> set[str]:
    """Executable names of running processes, plus long-lived daemons by name."""
    found: set[str] = set()
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            found.add(os.path.basename(os.readlink(f"/proc/{pid}/exe")))
            if b"GradleDaemon" in Path(f"/proc/{pid}/cmdline").read_bytes():
                found.add("GradleDaemon")
        except OSError:
            pass
    return found


def _make_writable(path: Path) -> None:
    """rmtree needs write access to directories. Links are never touched."""
    for current, directories, _ in os.walk(path, followlinks=False):
        for directory in [current, *(os.path.join(current, name) for name in directories)]:
            info = os.lstat(directory)
            if stat.S_ISDIR(info.st_mode) and info.st_mode & 0o700 != 0o700:
                os.chmod(directory, info.st_mode | 0o700)


def remove(path: Path) -> None:
    """Remove a file, link, or directory. Links are removed, never followed."""
    info = os.lstat(path)
    if stat.S_ISDIR(info.st_mode):
        _make_writable(path)
        shutil.rmtree(path)
    else:
        path.unlink()
    if os.path.lexists(path):
        raise OSError(f"still present: {path}")
