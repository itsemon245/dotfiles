"""Read-only worktree audit for sysclean. Nothing here changes a repository.

A check that cannot run leads to the status `unknown`, never `safe`.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from . import process
from .paths import xdg_config_home
from .sysclean_guard import users_of

SKIP_DIRECTORIES = {"node_modules", "vendor", ".venv", ".cache", ".git", "storage"}
GENERATED = {"node_modules", "vendor"}
LONG_LIVED = ("production", "staging", "main", "master", "develop", "dev")
RECENT_SESSION_DAYS = 7
GIT_ENV = {
    **os.environ,
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_SSH_COMMAND": "ssh -o BatchMode=yes -o ConnectTimeout=10",
}
STATUS_ORDER = (
    "in-use",
    "open-pr",
    "unpushed",
    "uncommitted",
    "unknown",
    "unmerged",
    "recent-session",
    "env-differs",
    "safe",
)


@dataclass
class Worktree:
    path: Path
    branch: str = ""
    last_commit: str = ""
    in_use: bool = False
    pr: str = "none"  # none, OPEN, MERGED, CLOSED, or unknown
    merged: bool = False
    unpushed: int = 0
    uncommitted: list[str] = field(default_factory=list)
    session_days: float | None = None
    env_differs: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    status: str = "unknown"


@dataclass
class Repository:
    common_dir: str
    main: Path
    slug: str | None = None
    heads: set[str] | None = None
    pull_requests: list[dict] | None = None
    tips: list[str] = field(default_factory=list)


def classify(tree: Worktree) -> str:
    """Pick the status. Reasons to keep a worktree always win."""
    if tree.in_use:
        return "in-use"
    if tree.pr == "OPEN":
        return "open-pr"
    if tree.unpushed:
        return "unpushed"
    if tree.uncommitted:
        return "uncommitted"
    if tree.failed or tree.pr == "unknown":
        return "unknown"
    if tree.session_days is not None and tree.session_days < RECENT_SESSION_DAYS:
        return "recent-session"
    if not tree.merged:
        return "unmerged"
    if tree.env_differs:
        return "env-differs"
    return "safe"


def _git(path: Path | str, *args: str, timeout: int = 60) -> tuple[int, str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), *args],
            capture_output=True,
            text=True,
            errors="replace",
            env=GIT_ENV,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    return result.returncode, result.stdout  # unstripped: porcelain column 1 can be a space


def discover(roots: list[Path]) -> list[Path]:
    """Find linked worktrees: a `.git` file pointing into a repo's worktrees folder."""
    found = []
    for root in roots:
        for current, directories, names in os.walk(root, followlinks=False):
            directories[:] = [name for name in directories if name not in SKIP_DIRECTORIES]
            if ".git" not in names:
                continue
            try:
                pointer = Path(current, ".git").read_text(errors="replace")
            except OSError:
                continue
            if pointer.startswith("gitdir:") and "/worktrees/" in pointer:
                found.append(Path(current))
                directories[:] = []
    return sorted(set(found))


def repo_slug(url: str) -> str | None:
    match = re.search(r"github\.com[:/](.+?)(?:\.git)?/?$", url.strip())
    return match.group(1) if match else None


def load_repository(common_dir: str, slugs: dict[str, str]) -> Repository:
    repository = Repository(common_dir, Path(common_dir).parent)
    code, url = _git(common_dir, "config", "--get", "remote.origin.url")
    repository.slug = slugs.get(str(repository.main)) or (repo_slug(url) if code == 0 else None)
    code, heads = _git(common_dir, "ls-remote", "--heads", "origin", timeout=45)
    if code == 0:
        repository.heads = {line.split()[0] for line in heads.splitlines() if line.strip()}
    for branch in LONG_LIVED:
        reference = f"refs/remotes/origin/{branch}"
        if _git(common_dir, "rev-parse", "-q", "--verify", reference)[0] == 0:
            repository.tips.append(reference)
    if repository.slug and process.command_exists("gh"):
        repository.pull_requests = _pull_requests(repository.slug)
    return repository


def _pull_requests(slug: str) -> list[dict] | None:
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--repo", slug, "--state", "all", "--limit", "3000", "--json", "number,state,headRefName,headRefOid"],
            capture_output=True,
            text=True,
            timeout=240,
        )
        return json.loads(result.stdout) if result.returncode == 0 else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def load_sessions() -> list[dict]:
    """Claude app sessions. No app data simply means no known sessions."""
    root = xdg_config_home() / "Claude" / "claude-code-sessions"
    sessions = []
    for path in root.rglob("*.json") if root.is_dir() else ():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and not data.get("isArchived"):
            sessions.append({"paths": (data.get("worktreePath") or "", data.get("cwd") or ""), "last": (data.get("lastActivityAt") or 0) / 1000})
    return sessions


def _unlanded(tree: Path, status: str, tips: list[str]) -> list[str]:
    """Changed files whose content is not on a long-lived branch."""
    changed = []
    for line in status.splitlines():
        code, name = line[:2], line[3:].strip('"')
        name = name.split(" -> ")[-1].rstrip("/")
        if code == "??" and name.split("/")[-1] in GENERATED:
            continue
        path = tree / name
        if path.is_file():
            code_hash, content = _git(tree, "hash-object", "--", name)
            blobs = [_git(tree, "rev-parse", "-q", "--verify", f"{tip}:{name}") for tip in tips]
            if code_hash == 0 and any(result[0] == 0 and result[1].strip() == content.strip() for result in blobs):
                continue
        elif not os.path.lexists(path) and any(_git(tree, "rev-parse", "-q", "--verify", f"{tip}:{name}")[0] != 0 for tip in tips):
            continue
        changed.append(name)
    return changed


def _hash(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _env_differences(tree: Path, main: Path) -> list[str]:
    """Names of untracked env files that differ. Values are hashed, never shown."""
    different = []
    for path in sorted(tree.glob(".env*")):
        if path.is_file() and path.name != ".env.example":
            tracked = _git(tree, "ls-files", "--error-unmatch", "--", path.name)[0] == 0
            if not tracked and _hash(path) != _hash(main / path.name):
                different.append(path.name)
    return different


def audit(path: Path, repository: Repository, sessions: list[dict], busy: bool, now: float) -> Worktree:
    tree = Worktree(path, in_use=busy)
    code, head = _git(path, "rev-parse", "HEAD")
    head = head.strip()
    if code != 0:
        tree.failed.append("head")
    tree.branch = _git(path, "symbolic-ref", "--short", "-q", "HEAD")[1].strip()
    tree.last_commit = _git(path, "log", "-1", "--format=%cs")[1].strip()

    code, status = _git(path, "status", "--porcelain", "--untracked-files=normal", timeout=120)
    if code != 0:
        tree.failed.append("status")
    else:
        tree.uncommitted = _unlanded(path, status, repository.tips)

    code, count = _git(path, "rev-list", "--count", "HEAD", "--not", "--remotes")
    if code != 0 or not count.strip().isdigit():
        tree.failed.append("unpushed")
    elif repository.heads is None or head not in repository.heads:
        tree.unpushed = int(count)

    ancestors = [tip for tip in repository.tips if _git(path, "merge-base", "--is-ancestor", "HEAD", tip)[0] == 0]
    tree.merged = bool(ancestors)
    if repository.pull_requests is None:
        tree.pr = "unknown"
    else:
        matches = [
            item
            for item in repository.pull_requests
            if (tree.branch and item["headRefName"] == tree.branch) or item["headRefOid"] == head
        ]
        if matches:
            latest = max(matches, key=lambda item: item["number"])
            tree.pr = latest["state"]
            tree.merged = tree.merged or (latest["state"] == "MERGED" and latest["headRefOid"] == head)

    mine = [
        session["last"]
        for session in sessions
        if any(value == str(path) or value.startswith(str(path) + "/") for value in session["paths"])
    ]
    tree.session_days = round((now - max(mine)) / 86400, 1) if mine else None
    tree.env_differs = _env_differences(path, repository.main)
    tree.status = classify(tree)
    return tree


def run_audit(roots: list[Path], slugs: dict[str, str]) -> list[Worktree]:
    paths = discover(roots)
    by_repository: dict[str, list[Path]] = defaultdict(list)
    orphans = []
    for path in paths:
        code, common = _git(path, "rev-parse", "--path-format=absolute", "--git-common-dir")
        if code == 0:
            by_repository[common.strip()].append(path)
        else:
            orphans.append(path)
    busy = users_of(paths)
    sessions = load_sessions()
    now = time.time()
    trees = [Worktree(path, failed=["repository"]) for path in orphans]
    for common, members in by_repository.items():
        repository = load_repository(common, slugs)
        trees.extend(audit(path, repository, sessions, path in busy, now) for path in members)
    for tree in trees:
        tree.status = classify(tree)
    return sorted(trees, key=lambda tree: (STATUS_ORDER.index(tree.status), str(tree.path)))


def reclaimable(paths: list[Path]) -> int:
    """Bytes freed if all paths vanish. A file counts once all its hardlinks are inside."""
    seen: dict[tuple[int, int], list[int]] = {}
    for root in paths:
        for current, directories, names in os.walk(root, followlinks=False):
            for name in directories + names:
                try:
                    info = os.lstat(os.path.join(current, name))
                except OSError:
                    continue
                entry = seen.setdefault((info.st_dev, info.st_ino), [0, info.st_nlink, info.st_blocks * 512])
                entry[0] += 1
    return sum(size for count, links, size in seen.values() if count >= links)
