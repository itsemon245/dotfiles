"""Find or replace one variable in every project's .env files. Previews unless --apply is given.

Roots are walked for .env files. Every Git repository found there also reports
its linked worktrees, so worktrees that live outside the roots are covered too.

Never touched: template files (.env.example, .env.sample, ...) and any file
inside a repository that git does not ignore, since a change there could be
committed. Skipped unless --file names them: .env.testing and .env.localtest.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .cli import ToolError
from .paths import home, xdg_state_home

DEFAULT_ROOTS = ("Work",)
SKIP_DIRECTORIES = {"node_modules", "vendor", ".git", ".venv", "venv", "__pycache__", ".cache", ".next", "storage"}
TEMPLATE_SUFFIXES = (".example", ".exmaple", ".sample", ".dist", ".template", ".tpl", ".bak", ".orig", ".swp")
# Skipped unless --file names them: test environments should not follow local changes.
DEFAULT_SKIPPED_NAMES = {".env.testing", ".env.localtest"}
KEY_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*")
GIT_ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"}


@dataclass
class Match:
    path: Path
    lines: list[tuple[int, str]]  # (1-based line number, current value)
    text: str  # whole file, line endings preserved
    updated: str  # file after replacement


def backup_root() -> Path:
    return xdg_state_home() / "dotfiles" / "backups" / "env-replace"


def is_env_file(name: str) -> bool:
    if name != ".env" and not name.startswith(".env."):
        return False
    return not name.endswith(TEMPLATE_SUFFIXES)


def _line_pattern(key: str) -> re.Pattern[str]:
    return re.compile(rf"^(\s*(?:export\s+)?{re.escape(key)}[ \t]*=[ \t]*)(.*?)(\r?\n)?$")


def _walk(root: Path, env_files: set[Path], repos: set[Path]) -> None:
    for current, directories, names in os.walk(root, followlinks=False):
        if ".git" in names or ".git" in directories:
            repos.add(Path(current))
        directories[:] = [name for name in directories if name not in SKIP_DIRECTORIES]
        for name in names:
            if is_env_file(name):
                env_files.add(Path(current, name))


def linked_worktrees(repo: Path) -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
            errors="replace",
            env=GIT_ENV,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    trees = [Path(line[len("worktree ") :]) for line in result.stdout.splitlines() if line.startswith("worktree ")]
    return [tree for tree in trees if tree.is_dir()]


def _inside(path: Path, roots: list[Path]) -> bool:
    return any(path == root or path.is_relative_to(root) for root in roots)


def discover(roots: list[Path]) -> list[Path]:
    """Every .env file under the roots and under any worktree of a repo found there."""
    env_files: set[Path] = set()
    repos: set[Path] = set()
    walked = [root.resolve() for root in roots]
    for root in walked:
        _walk(root, env_files, repos)

    seen_repos: set[Path] = set()
    pending = list(repos)
    while pending:
        repo = pending.pop()
        if repo in seen_repos:
            continue
        seen_repos.add(repo)
        for tree in linked_worktrees(repo):
            tree = tree.resolve()
            if _inside(tree, walked):
                continue
            walked.append(tree)
            found: set[Path] = set()
            _walk(tree, env_files, found)
            pending.extend(found - seen_repos)

    resolved = set()
    backups = backup_root().resolve()
    for path in env_files:
        try:
            real = path.resolve(strict=True)
        except OSError:
            continue
        if real.is_file() and not real.is_relative_to(backups):
            resolved.add(real)
    return sorted(resolved)


def _git_run(directory: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", "-C", str(directory), *args],
            input=stdin,
            capture_output=True,
            text=True,
            errors="surrogateescape",
            env=GIT_ENV,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def committable(paths: list[Path]) -> set[Path]:
    """Files git could commit: inside a work tree and tracked or not ignored.

    A file outside any repository is safe. If git cannot answer for a file inside
    a repository, the file counts as committable, so it is left alone.
    """
    by_directory: dict[Path, list[Path]] = {}
    for path in paths:
        by_directory.setdefault(path.parent, []).append(path)
    risky: set[Path] = set()
    for directory, files in by_directory.items():
        names = "".join(f"{path.name}\0" for path in files)
        result = _git_run(directory, "check-ignore", "--stdin", "-z", stdin=names)
        if result is not None and result.returncode in (0, 1):
            ignored = set(result.stdout.split("\0"))
            risky.update(path for path in files if path.name not in ignored)
            continue
        inside = _git_run(directory, "rev-parse", "--is-inside-work-tree")
        if inside is None or inside.returncode == 0:
            risky.update(files)
    return risky


def plan(paths: list[Path], key: str, value: str | None) -> list[Match]:
    pattern = _line_pattern(key)
    matches = []
    for path in paths:
        try:
            with path.open(encoding="utf-8", errors="surrogateescape", newline="") as handle:
                text = handle.read()
        except OSError:
            continue
        found: list[tuple[int, str]] = []
        out: list[str] = []
        for number, line in enumerate(text.splitlines(keepends=True), start=1):
            hit = pattern.match(line)
            if not hit:
                out.append(line)
                continue
            found.append((number, hit.group(2)))
            out.append(line if value is None else f"{hit.group(1)}{value}{hit.group(3) or ''}")
        if found:
            matches.append(Match(path, found, text, "".join(out)))
    return matches


def write(match: Match, stamp: str) -> Path:
    """Back up the file, then replace it atomically with the same permissions."""
    backup = backup_root() / stamp / str(match.path).lstrip("/")
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(match.path, backup)
    descriptor, temporary = tempfile.mkstemp(prefix=".env-replace-", dir=match.path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", errors="surrogateescape", newline="") as handle:
            handle.write(match.updated)
        shutil.copymode(match.path, temporary)
        os.replace(temporary, match.path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
    return backup


def mask(value: str) -> str:
    return f"<{len(value)} chars>" if value else "<empty>"


def _display(path: Path) -> str:
    try:
        return "~/" + str(path.relative_to(home().resolve()))
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="env-replace", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("key", help="variable name, e.g. DB_HOST")
    parser.add_argument("value", nargs="?", help="new value, written as given (add quotes yourself); omit to only list")
    parser.add_argument("--apply", action="store_true", help="write the changes (backups go to ~/.local/state/dotfiles/backups/env-replace)")
    parser.add_argument("--root", action="append", metavar="DIR", help="directory to search; repeatable (default: ~/Work)")
    parser.add_argument(
        "--file",
        action="append",
        metavar="GLOB",
        help="only touch files whose name matches, e.g. --file .env --file '.env.local'; repeatable (default: every .env*)",
    )
    parser.add_argument("--show-values", action="store_true", help="print current values instead of masking them")
    args = parser.parse_args(argv)

    if not KEY_PATTERN.fullmatch(args.key):
        raise ToolError(f"not a valid variable name: {args.key!r}")
    if args.value is not None and ("\n" in args.value or "\r" in args.value):
        raise ToolError("the value must be a single line")
    if args.apply and args.value is None:
        raise ToolError("--apply needs a value")

    roots = [Path(root).expanduser() for root in args.root] if args.root else [home() / root for root in DEFAULT_ROOTS]
    missing = [str(root) for root in roots if not root.is_dir()]
    if missing:
        raise ToolError(f"root not found: {', '.join(missing)}")

    paths = discover(roots)
    if args.file:
        paths = [path for path in paths if any(fnmatch.fnmatchcase(path.name, glob) for glob in args.file)]
    else:
        paths = [path for path in paths if path.name not in DEFAULT_SKIPPED_NAMES]
    risky = committable(paths)
    skipped = plan(sorted(risky), args.key, None)
    for match in skipped:
        print(f"{'skipped':13} {_display(match.path)}  (not ignored by git, a change could be committed)")
    if skipped:
        print()
    matches = plan([path for path in paths if path not in risky], args.key, args.value)
    if not matches:
        print(f"No other .env file sets {args.key}." if skipped else f"No .env file sets {args.key}.")
        return 0

    show = (lambda value: value) if args.show_values else mask
    changed = [match for match in matches if match.updated != match.text]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for match in matches:
        if args.value is None:
            state = "found"
        elif match not in changed:
            state = "unchanged"
        else:
            state = "updated" if args.apply else "would update"
        print(f"{state:13} {_display(match.path)}")
        for number, current in match.lines:
            print(f"{'':13}   line {number}: {args.key}={show(current)}")
        if args.apply and match in changed:
            write(match, stamp)

    print()
    if args.value is None:
        print(f"{len(matches)} file(s) set {args.key}.")
    elif args.apply:
        backups = f" Backups: {_display(backup_root() / stamp)}" if changed else ""
        print(f"Updated {len(changed)} of {len(matches)} file(s).{backups}")
    else:
        print(f"{len(changed)} of {len(matches)} file(s) would change. Run again with --apply to write them.")
    return 0
