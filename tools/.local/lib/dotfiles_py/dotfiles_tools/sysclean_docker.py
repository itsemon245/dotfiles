"""Docker rules for sysclean. Removal is by exact ID or name, and never forced."""

from __future__ import annotations

import fnmatch
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime

from . import process
from .cli import ToolError

PROBE_IMAGE = "alpine:latest"
# Reads a marker per volume. Mounted read-only, with no network and no pull.
PROBE_SCRIPT = (
    'for d in /v/*; do n=$(basename "$d"); k=other; '
    '[ -z "$(ls -A "$d")" ] && k=empty; '
    '[ -e "$d/PG_VERSION" ] || [ -e "$d/data/PG_VERSION" ] || [ -e "$d/18/docker/PG_VERSION" ] && k=postgres; '
    '[ -d "$d/mysql" ] && k=mysql; '
    '[ -e "$d/dump.rdb" ] && k=redis; '
    'echo "$n $k"; done'
)


@dataclass(frozen=True)
class Image:
    id: str
    tags: tuple[str, ...]
    size: int
    created: datetime | None

    @property
    def label(self) -> str:
        return ", ".join(self.tags) or self.id.removeprefix("sha256:")[:12]


@dataclass(frozen=True)
class Volume:
    name: str
    size: str
    project: str
    kind: str


def _docker(*args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


def available() -> bool:
    if not process.command_exists("docker"):
        return False
    try:
        return _docker("info", "--format", "{{.ID}}", timeout=15).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _output(*args: str) -> str:
    result = _docker(*args)
    if result.returncode != 0:
        raise ToolError(f"docker {args[0]} failed: {result.stderr.strip()[:160]}")
    return result.stdout


def images() -> list[Image]:
    ids = sorted(set(_output("images", "--no-trunc", "-q").split()))
    if not ids:
        return []
    found = []
    for item in json.loads(_output("image", "inspect", *ids)):
        try:
            created = datetime.fromisoformat(item["Created"])
        except (KeyError, TypeError, ValueError):
            created = None
        found.append(Image(item["Id"], tuple(item.get("RepoTags") or ()), int(item.get("Size") or 0), created))
    return found


def used_image_ids() -> set[str]:
    """Images used by any container, including stopped ones."""
    containers = _output("ps", "-aq", "--no-trunc").split()
    if not containers:
        return set()
    return set(_output("inspect", "--format", "{{.Image}}", *containers).split())


def is_protected(image: Image, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatchcase(tag, pattern) for tag in image.tags for pattern in patterns)


def candidates(
    all_images: list[Image],
    used: set[str],
    protected: tuple[str, ...],
    *,
    tagged: bool,
    now: datetime,
    min_age_days: int,
) -> list[Image]:
    """Dangling images old enough to remove, or unused tagged ones when asked."""
    chosen = []
    for image in all_images:
        if image.id in used or is_protected(image, protected) or bool(image.tags) != tagged:
            continue
        if image.created is None or (now - image.created).days < min_age_days:
            continue
        chosen.append(image)
    return sorted(chosen, key=lambda image: -image.size)


def remove_image(image: Image) -> str | None:
    """Return an error, or None. Tags are removed one by one, by exact name."""
    for reference in image.tags or (image.id,):
        result = _docker("rmi", reference)
        if result.returncode != 0:
            return result.stderr.strip()[:160]
    return None


def unattached_volumes() -> list[Volume]:
    names = sorted(_output("volume", "ls", "-q", "--filter", "dangling=true").split())
    if not names:
        return []
    sizes: dict[str, str] = {}
    for line in _output("system", "df", "-v", "--format", "{{json .}}").splitlines():
        for volume in json.loads(line).get("Volumes") or []:
            sizes[volume.get("Name", "")] = volume.get("Size", "?")
    kinds = _probe(names)
    found = []
    for item in json.loads(_output("volume", "inspect", *names)):
        labels = item.get("Labels") or {}
        name = item["Name"]
        found.append(Volume(name, sizes.get(name, "?"), labels.get("com.docker.compose.project", "-"), kinds.get(name, "unknown")))
    return found


def _probe(names: list[str]) -> dict[str, str]:
    """Identify volume contents. Skipped when the small probe image is not local."""
    if _docker("image", "inspect", PROBE_IMAGE).returncode != 0:
        return {}
    mounts = [argument for name in names for argument in ("-v", f"{name}:/v/{name}:ro")]
    result = _docker("run", "--rm", "--pull", "never", "--network", "none", *mounts, PROBE_IMAGE, "sh", "-c", PROBE_SCRIPT)
    if result.returncode != 0:
        return {}
    return dict(line.split(None, 1) for line in result.stdout.splitlines() if " " in line)
