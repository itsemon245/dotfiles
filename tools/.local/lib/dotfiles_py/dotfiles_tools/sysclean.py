"""Report, clean, and watch disk usage. Previews unless --apply is given."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import tomllib
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from . import notify, process, sysclean_docker as docker, sysclean_guard as guard, sysclean_worktrees as worktrees
from .cli import ToolError
from .paths import xdg_config_home, xdg_state_home

GIB = 1024**3
SERVICE = "sysclean"
BROWSERS = ("chrome", "firefox", "firefox-bin", "chromium")
BUILDERS = ("yay", "paru", "pacman", "makepkg")
PROTECTED_IMAGES = ("my/php:*", "php:*-cli")
DEFAULT_ROOTS = ("Work", "Projects", ".codex/worktrees", "Documents")
INFO_PATHS = (
    ("Steam library", ".local/share/Steam/steamapps"),
    ("LM Studio", ".lmstudio"),
    ("Heroic tools", ".config/heroic/tools"),
)
PACMAN_CONFIG = Path("/etc/conf.d/pacman-contrib")
COREDUMP_CONFIG = Path("/etc/systemd/coredump.conf.d")
COREDUMPS = Path("/var/lib/systemd/coredump")
PACMAN_CACHE = Path("/var/cache/pacman/pkg")


@dataclass(frozen=True)
class Rule:
    name: str
    path: str
    level: int
    whole: bool = False  # remove the directory itself, not only its contents
    min_age_days: int = 0
    blocked_by: tuple[str, ...] = ()


@dataclass
class Config:
    warn_gb: float = 30
    critical_gb: float = 10
    age_days: int = 30
    rules: list[Rule] = field(default_factory=list)
    protected_images: tuple[str, ...] = PROTECTED_IMAGES
    roots: tuple[str, ...] = DEFAULT_ROOTS
    repos: dict[str, str] = field(default_factory=dict)


@dataclass
class RulePlan:
    rule: Rule
    items: list[tuple[Path, int]] = field(default_factory=list)
    kept: int = 0
    skipped: str | None = None

    @property
    def size(self) -> int:
        return sum(size for _, size in self.items)


def default_rules(age_days: int) -> list[Rule]:
    return [
        Rule("AUR build cache (yay)", ".cache/yay", 1, min_age_days=age_days, blocked_by=BUILDERS),
        Rule("AUR build cache (paru)", ".cache/paru", 1, min_age_days=age_days, blocked_by=BUILDERS),
        Rule("uv cache", ".cache/uv", 2),
        Rule("npm cache", ".npm/_cacache", 2),
        Rule("pnpm metadata cache", ".cache/pnpm", 2),
        Rule("Gradle cache", ".gradle/caches", 2, blocked_by=("GradleDaemon",)),
        Rule("Go build cache", ".cache/go-build", 2),
        Rule("pip cache", ".cache/pip", 2),
        Rule("Composer cache", ".cache/composer", 2),
        Rule("Chrome cache", ".cache/google-chrome", 2, blocked_by=BROWSERS),
        Rule("Chromium cache", ".cache/chromium", 2, blocked_by=BROWSERS),
        Rule("Firefox cache", ".cache/mozilla", 2, blocked_by=BROWSERS),
    ]


def load_config(path: Path | None = None) -> Config:
    """Machine-specific settings live outside this public repo."""
    path = path or xdg_config_home() / "sysclean" / "local.toml"
    data: dict[str, Any] = {}
    if path.exists():
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ToolError(f"could not read {path}: {error}") from error
    config = Config()
    watch = data.get("watch", {})
    config.warn_gb = float(watch.get("warn_gb", config.warn_gb))
    config.critical_gb = float(watch.get("critical_gb", config.critical_gb))
    config.age_days = int(data.get("age_days", config.age_days))
    config.protected_images = PROTECTED_IMAGES + tuple(data.get("docker", {}).get("protected", ()))
    trees = data.get("worktrees", {})
    config.roots = tuple(trees.get("roots", DEFAULT_ROOTS))
    config.repos = dict(trees.get("repos", {}))
    config.rules = default_rules(config.age_days)
    for item in data.get("rules", []):
        try:
            level = int(item["level"])
            if level not in (1, 2, 3):
                raise ValueError(level)
            config.rules.append(Rule(str(item.get("name", item["path"])), str(item["path"]), level, bool(item.get("whole", False))))
        except (KeyError, TypeError, ValueError) as error:
            raise ToolError(f"invalid rule in {path}: {item}") from error
    return config


def human(size: float) -> str:
    return f"{size / GIB:.2f}G" if size >= GIB / 10 else f"{size / 1024**2:.0f}M"


def plan_rule(rule: Rule, base: Path, now: float, running: set[str], busy: dict[Path, set[str]]) -> RulePlan:
    plan = RulePlan(rule)
    root, reason = guard.check_target(base, rule.path)
    if root is None:
        plan.skipped = reason
        return plan
    if root in busy:
        plan.skipped = "in use by " + ", ".join(sorted(busy[root])[:3])
        return plan
    blockers = sorted(running.intersection(rule.blocked_by))
    if blockers:
        plan.skipped = "running: " + ", ".join(blockers)
        return plan
    entries = [root] if rule.whole else sorted(root.iterdir())
    cutoff = now - rule.min_age_days * 86400
    try:
        for entry in entries:
            usage = guard.measure(entry)
            if rule.min_age_days and usage.newest > cutoff:
                plan.kept += 1
            else:
                plan.items.append((entry, usage.size))
    except (ToolError, OSError) as error:
        plan.items.clear()
        plan.skipped = str(error)
    return plan


def plan_rules(rules: list[Rule], base: Path) -> list[RulePlan]:
    roots = [path for path in (guard.check_target(base, rule.path)[0] for rule in rules) if path]
    busy = guard.users_of(roots)
    running = guard.running_commands()
    return [plan_rule(rule, base, time.time(), running, busy) for rule in rules]


def confirm(question: str) -> bool:
    """Level 3 is per-item. Without a terminal the answer is always no."""
    if not sys.stdin.isatty():
        return False
    return input(f"{question} [y/N] ").strip().lower() == "y"


def docker_images(level: int, config: Config) -> tuple[list[docker.Image], list[docker.Image], str | None]:
    """Dangling and unused tagged images, or why Docker rules are skipped."""
    if not docker.available():
        return [], [], "Docker is not available"
    try:
        images = docker.images()
        used = docker.used_image_ids()
    except (ToolError, OSError, ValueError) as error:
        return [], [], str(error)
    now = datetime.now().astimezone()
    dangling = docker.candidates(images, used, config.protected_images, tagged=False, now=now, min_age_days=config.age_days)
    tagged = docker.candidates(images, used, config.protected_images, tagged=True, now=now, min_age_days=0) if level >= 3 else []
    return dangling, tagged, None


def clean(level: int, apply: bool, config: Config, base: Path) -> dict[str, Any]:
    base = guard.check_base(base)
    summary: dict[str, Any] = {"planned": 0, "removed": 0, "skipped": [], "failed": []}
    start = shutil.disk_usage(base).free

    def remove_paths(plan: RulePlan) -> None:
        for path, _ in plan.items:
            try:
                guard.remove(path)
                summary["removed"] += 1
            except OSError as error:
                summary["failed"].append(f"{path}: {error}")

    for plan in plan_rules([rule for rule in config.rules if rule.level <= level], base):
        if plan.skipped:
            if plan.skipped != "missing":
                summary["skipped"].append(f"{plan.rule.name}: {plan.skipped}")
                print(f"SKIP    {plan.rule.name}: {plan.skipped}")
            continue
        if not plan.items:
            continue
        kept = f" ({plan.kept} recent kept)" if plan.kept else ""
        summary["planned"] += plan.size
        verb = "REMOVE " if apply else "PREVIEW"
        print(f"{verb} {human(plan.size):>8}  {plan.rule.name}{kept}")
        if not apply:
            continue
        if plan.rule.level == 3 and not confirm(f"Remove {plan.rule.name} ({human(plan.size)})?"):
            summary["skipped"].append(f"{plan.rule.name}: not confirmed")
            continue
        remove_paths(plan)

    dangling, tagged, reason = docker_images(level, config)
    if reason:
        summary["skipped"].append(f"Docker: {reason}")
        print(f"SKIP    Docker: {reason}")
    for image, needs_confirmation in [(item, False) for item in dangling] + [(item, True) for item in tagged]:
        summary["planned"] += image.size
        print(f"{'REMOVE ' if apply else 'PREVIEW'} {human(image.size):>8}  Docker image {image.label}")
        if not apply:
            continue
        if needs_confirmation and not confirm(f"Remove image {image.label}?"):
            summary["skipped"].append(f"{image.label}: not confirmed")
            continue
        error = docker.remove_image(image)
        if error:
            summary["failed"].append(f"{image.label}: {error}")
        else:
            summary["removed"] += 1

    if level >= 2 and process.command_exists("pnpm"):
        print(f"{'RUN    ' if apply else 'PREVIEW'} {'':>8}  pnpm store prune")
        if apply and process.run(["pnpm", "store", "prune"], quiet=True).returncode != 0:
            summary["failed"].append("pnpm store prune")

    summary["freed"] = max(0, shutil.disk_usage(base).free - start)
    if apply:
        print(f"Freed {human(summary['freed'])}.")
    else:
        print(f"Would free up to {human(summary['planned'])}. Nothing changed; use --apply to clean.")
    for failure in summary["failed"]:
        print(f"FAILED  {failure}", file=sys.stderr)
    return summary


def post_summary(summary: dict[str, Any], level: int, apply: bool) -> None:
    if not summary["planned"] and not summary["failed"]:
        return  # a weekly "nothing to do" is only noise
    details = []
    if summary["skipped"]:
        details.append(f"{len(summary['skipped'])} skipped")
    if summary["failed"]:
        details.append(f"{len(summary['failed'])} failed")
    suffix = f" ({', '.join(details)})" if details else ""
    if apply:
        title = "🧹 Cleanup finished"
        body = f"Level {level} freed {human(summary['freed'])}{suffix}."
    else:
        title = "🧹 Cleanup preview"
        body = f"Level {level} could free {human(summary['planned'])}{suffix}. Nothing was removed."
    notify.post(
        SERVICE,
        title,
        body,
        icon="user-trash",
        urgency="critical" if summary["failed"] else "normal",
        key="sysclean-clean",
        ttl=7 * 86400,
    )


def watch_state_file() -> Path:
    return xdg_state_home() / SERVICE / "watch.json"


def disk_level(free: float, config: Config) -> str:
    gib = free / GIB
    if gib < config.critical_gb:
        return "critical"
    return "warning" if gib < config.warn_gb else "ok"


def watch(config: Config, path: Path = Path("/")) -> int:
    """Notify once per crossing into a worse level. Never removes anything."""
    free = shutil.disk_usage(path).free
    level = disk_level(free, config)
    state_file = watch_state_file()
    try:
        previous = json.loads(state_file.read_text(encoding="utf-8")).get("level", "ok")
    except (OSError, ValueError, AttributeError):
        previous = "ok"
    order = ("ok", "warning", "critical")
    if order.index(level) > order.index(previous if previous in order else "ok"):
        try:
            plans = plan_rules([rule for rule in config.rules if rule.level <= 2], guard.check_base(guard.real_home()))
            hint = f" About {human(sum(plan.size for plan in plans))} can be cleaned with sysclean clean --level 2."
        except (ToolError, OSError):
            hint = " Run sysclean report."
        notify.post(
            SERVICE,
            "💾 Disk space critical" if level == "critical" else "💾 Disk space low",
            f"{human(free)} free on {path}.{hint}",
            icon="drive-harddisk",
            urgency="critical" if level == "critical" else "normal",
            key="sysclean-low-disk",
        )
    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps({"level": level}), encoding="utf-8")
    except OSError as error:
        print(f"sysclean: could not save watch state: {error}", file=sys.stderr)
    print(f"{human(free)} free on {path}: {level}")
    return 0


def _directory_size(path: Path) -> int | None:
    try:
        return sum(entry.stat(follow_symlinks=False).st_blocks * 512 for entry in os.scandir(path))
    except OSError:
        return None


def root_owned_status() -> list[dict[str, str]]:
    """Items only root can clean, and the setting that keeps each one in check."""
    rows = []
    pacman_size = _directory_size(PACMAN_CACHE)
    try:
        configured = "-k2" in PACMAN_CONFIG.read_text(encoding="utf-8")
    except OSError:
        configured = False
    rows.append({
        "name": "Pacman cache",
        "size": human(pacman_size) if pacman_size is not None else "unknown",
        "advice": "ok" if configured else f"set PACCACHE_ARGS='-k2' in {PACMAN_CONFIG}",
    })
    dump_size = _directory_size(COREDUMPS)
    rows.append({
        "name": "Coredumps",
        "size": human(dump_size) if dump_size is not None else "unknown",
        "advice": "ok" if COREDUMP_CONFIG.is_dir() else f"add MaxUse= under {COREDUMP_CONFIG}",
    })
    return rows


def orphaned_packages() -> list[str] | None:
    if not process.command_exists("pacman"):
        return None
    return process.command_lines(["pacman", "-Qdtq"])


def report_data(config: Config, base: Path) -> dict[str, Any]:
    base = guard.check_base(base)
    usage = shutil.disk_usage(base)
    plans = plan_rules([rule for rule in config.rules if rule.level <= 3], base)
    dangling, tagged, docker_reason = docker_images(3, config)
    volumes: list[docker.Volume] | None = None
    if docker_reason is None:
        try:
            volumes = docker.unattached_volumes()
        except (ToolError, OSError, ValueError) as error:
            docker_reason = str(error)
    info = []
    for name, relative in INFO_PATHS:
        path = base / relative
        if path.is_dir():
            try:
                info.append({"name": name, "size": human(guard.measure(path).size)})
            except (ToolError, OSError):
                pass
    roots = [base / root for root in config.roots if (base / root).is_dir()]
    orphans = orphaned_packages()
    return {
        "free": human(usage.free),
        "total": human(usage.total),
        "levels": {
            str(level): [
                {"name": plan.rule.name, "size": human(plan.size), "bytes": plan.size, "kept": plan.kept, "skipped": plan.skipped}
                for plan in plans
                if plan.rule.level == level and plan.skipped != "missing" and (plan.items or plan.skipped)
            ]
            for level in (1, 2, 3)
        },
        "docker": {
            "unavailable": docker_reason,
            "dangling": [{"image": image.label, "size": human(image.size)} for image in dangling],
            "unused_tagged": [{"image": image.label, "size": human(image.size)} for image in tagged],
            "unattached_volumes": None if volumes is None else [asdict(volume) for volume in volumes],
        },
        "root_owned": root_owned_status(),
        "orphaned_packages": orphans,
        "worktrees": len(worktrees.discover(roots)),
        "large": info,
    }


def print_report(data: dict[str, Any]) -> None:
    print(f"Free: {data['free']} of {data['total']}\n")
    titles = {"1": "Level 1: safe", "2": "Level 2: caches", "3": "Level 3: review"}
    for level, title in titles.items():
        print(title)
        rows = data["levels"][level]
        for row in rows:
            state = f"skipped: {row['skipped']}" if row["skipped"] else (f"{row['kept']} recent kept" if row["kept"] else "")
            print(f"  {row['size']:>8}  {row['name']}  {state}".rstrip())
        if level == "1":
            for image in data["docker"]["dangling"]:
                print(f"  {image['size']:>8}  Docker image {image['image']}")
        if level == "3":
            for image in data["docker"]["unused_tagged"]:
                print(f"  {image['size']:>8}  Docker image {image['image']}")
        print()
    print("Level 4: report only")
    if data["docker"]["unavailable"]:
        print(f"  Docker unavailable: {data['docker']['unavailable']}")
    elif data["docker"]["unattached_volumes"] is not None:
        print(f"  Unattached Docker volumes: {len(data['docker']['unattached_volumes'])} (sysclean volumes)")
    print(f"  Worktrees: {data['worktrees']} (sysclean worktrees)")
    orphans = data["orphaned_packages"]
    print("  Orphaned packages: " + ("unavailable" if orphans is None else f"{len(orphans)}" + (f" ({', '.join(orphans[:6])})" if orphans else "")))
    for item in data["large"]:
        print(f"  {item['size']:>8}  {item['name']}")
    print("\nNeeds root (not cleaned by this tool)")
    for row in data["root_owned"]:
        print(f"  {row['size']:>8}  {row['name']}: {row['advice']}")


def print_worktrees(trees: list[worktrees.Worktree], home: Path) -> None:
    groups: dict[str, list[worktrees.Worktree]] = {}
    for tree in trees:
        groups.setdefault(tree.status, []).append(tree)
    for status, members in groups.items():
        size = worktrees.reclaimable([tree.path for tree in members])
        print(f"{status}: {len(members)}, about {human(size)} if all removed")
        for tree in members:
            label = str(tree.path).replace(str(home), "~", 1)
            extra = []
            if tree.pr not in ("none", "unknown"):
                extra.append(f"PR {tree.pr}")
            if tree.unpushed:
                extra.append(f"{tree.unpushed} unpushed")
            if tree.uncommitted:
                extra.append(f"{len(tree.uncommitted)} changed")
            if tree.env_differs:
                extra.append("env differs: " + ", ".join(tree.env_differs))
            if tree.failed:
                extra.append("failed: " + ", ".join(tree.failed))
            if tree.pr == "unknown":
                extra.append("PR unknown")
            if tree.session_days is not None:
                extra.append(f"session {tree.session_days}d ago")
            print(f"  {label} [{tree.branch or 'detached'}] {tree.last_commit}  {'; '.join(extra)}".rstrip())
        print()


def tree_json(tree: worktrees.Worktree) -> dict[str, Any]:
    return {**asdict(tree), "path": str(tree.path)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sysclean", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    report = commands.add_parser("report", help="read-only report of all levels")
    report.add_argument("--json", action="store_true")

    cleaner = commands.add_parser("clean", help="preview a cleanup, or apply it with --apply")
    cleaner.add_argument("--level", type=int, choices=(1, 2, 3), default=1)
    cleaner.add_argument("--apply", action="store_true", help="actually remove things")
    cleaner.add_argument("--notify", action="store_true", help="post the result as a notification")
    cleaner.add_argument("--notify-start", action="store_true", help="also post a notice before starting")

    trees = commands.add_parser("worktrees", help="read-only worktree status")
    trees.add_argument("--json", action="store_true")

    commands.add_parser("volumes", help="read-only summary of unattached Docker volumes")
    commands.add_parser("watch", help="check free space and notify when low")

    args = parser.parse_args(argv)
    config = load_config()
    home = guard.real_home()

    if args.command == "report":
        data = report_data(config, home)
        print(json.dumps(data, indent=1)) if args.json else print_report(data)
        return 0
    if args.command == "clean":
        if args.notify_start:
            notify.post(SERVICE, "🧹 Cleanup starting", f"Level {args.level}.", icon="user-trash", key="sysclean-clean", ttl=3600)
        summary = clean(args.level, args.apply, config, home)
        if args.notify:
            post_summary(summary, args.level, args.apply)
        return 1 if summary["failed"] else 0
    if args.command == "worktrees":
        process.require("git")
        found = worktrees.run_audit([home / root for root in config.roots if (home / root).is_dir()], config.repos)
        print(json.dumps([tree_json(tree) for tree in found], indent=1, default=str)) if args.json else print_worktrees(found, home)
        return 0
    if args.command == "volumes":
        process.require("docker")
        if not docker.available():
            raise ToolError("Docker is not running")
        volumes = docker.unattached_volumes()
        for volume in volumes:
            print(f"{volume.size:>9}  {volume.kind:<9} {volume.project:<14} {volume.name[:32]}")
        print(f"{len(volumes)} unattached. This tool never removes volumes.")
        return 0
    return watch(config)
