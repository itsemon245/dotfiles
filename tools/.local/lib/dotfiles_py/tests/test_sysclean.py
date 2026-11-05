from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotfiles_tools import sysclean, sysclean_docker as docker, sysclean_guard as guard, sysclean_worktrees as worktrees
from dotfiles_tools.cli import ToolError

HOSTILE_NAMES = ["sp ace", "qu'ote", 'dou"ble', "back\\slash", "$(touch PWNED)", "`x`", "*", "-rf", "new\nline"]
GIB = 1024**3


class TempHome(unittest.TestCase):
    """Every test works in a throwaway home. Real data is never reachable."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(os.path.realpath(temp.name))
        self.assertNotEqual(self.base, guard.real_home())
        self.assertTrue(self.base.is_relative_to(os.path.realpath(tempfile.gettempdir())))
        env = patch.dict(os.environ, {"XDG_STATE_HOME": str(self.base / "state"), "XDG_CONFIG_HOME": str(self.base / "config")})
        env.start()
        self.addCleanup(env.stop)
        no_docker = patch.object(docker, "available", return_value=False)
        no_docker.start()
        self.addCleanup(no_docker.stop)
        no_pnpm = patch.object(sysclean.process, "command_exists", return_value=False)
        no_pnpm.start()
        self.addCleanup(no_pnpm.stop)

    def put(self, relative: str, age_days: int = 0) -> Path:
        path = self.base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("data")
        if age_days:
            stamp = time.time() - age_days * 86400
            os.utime(path, (stamp, stamp))
            os.utime(path.parent, (stamp, stamp))
        return path

    def config(self, *rules: sysclean.Rule) -> sysclean.Config:
        return sysclean.Config(rules=list(rules))

    def run_clean(self, config: sysclean.Config, *, level: int = 3, apply: bool = True) -> dict:
        with patch("builtins.print"):
            return sysclean.clean(level, apply, config, self.base)


class GuardTest(TempHome):
    def test_base_must_be_the_real_home_or_a_throwaway(self) -> None:
        self.assertEqual(guard.check_base(self.base), self.base)
        for bad in (Path("/"), Path("/etc"), Path("/home"), Path(tempfile.gettempdir())):
            with self.subTest(bad=bad), self.assertRaises(ToolError):
                guard.check_base(bad)

    def test_real_home_ignores_a_faked_home_variable(self) -> None:
        with patch.dict(os.environ, {"HOME": "/tmp/fake"}):
            self.assertNotEqual(str(guard.real_home()), "/tmp/fake")

    def test_refuses_bad_relative_paths(self) -> None:
        for relative in ("", "/etc", "..", "a/../b", "a//b", "./a", ".cache/.."):
            with self.subTest(relative=relative):
                self.assertEqual(guard.check_target(self.base, relative), (None, "invalid path"))

    def test_refuses_paths_that_contain_or_sit_inside_protected_ones(self) -> None:
        self.put(".ssh/id_key")
        self.put(".local/share/Steam/steamapps/downloading/big")
        self.put("dotfiles/keep")
        self.put("Work/project/.env")
        for relative in (".ssh", ".local", ".local/share", ".local/share/Steam/steamapps/downloading", "dotfiles/x", "Work", ".config"):
            with self.subTest(relative=relative):
                path, reason = guard.check_target(self.base, relative)
                self.assertIsNone(path)
                self.assertIn("protected", reason)

    def test_allows_a_folder_inside_a_project(self) -> None:
        self.put("Work/project/node_modules/.cache/x/file")
        path, reason = guard.check_target(self.base, "Work/project/node_modules/.cache/x")
        self.assertIsNone(reason)
        self.assertEqual(path, self.base / "Work/project/node_modules/.cache/x")

    def test_refuses_a_symlinked_target(self) -> None:
        outside = self.put("outside/keep")
        (self.base / ".cache").mkdir()
        (self.base / ".cache/uv").symlink_to(outside.parent)
        path, reason = guard.check_target(self.base, ".cache/uv")
        self.assertIsNone(path)
        self.assertIn("resolves to", reason)

    def test_detects_a_process_using_a_target(self) -> None:
        file = self.put(".cache/uv/open-file")
        with file.open():
            self.assertIn(self.base / ".cache/uv", guard.users_of([self.base / ".cache/uv"]))

    def test_remove_never_follows_links(self) -> None:
        keep = self.put("outside/keep")
        target = self.base / "target"
        target.mkdir()
        (target / "dir-link").symlink_to(keep.parent)
        (target / "file-link").symlink_to(keep)
        guard.remove(target)
        self.assertFalse(target.exists())
        self.assertTrue(keep.exists())

    def test_removes_read_only_directories(self) -> None:
        file = self.put("target/locked/deep/file")
        os.chmod(file.parent, 0o500)
        os.chmod(file.parent.parent, 0o500)
        guard.remove(self.base / "target")
        self.assertFalse((self.base / "target").exists())


class CleanTest(TempHome):
    def test_preview_changes_nothing(self) -> None:
        file = self.put(".cache/uv/archive/file")
        summary = self.run_clean(self.config(sysclean.Rule("uv", ".cache/uv", 2)), apply=False)
        self.assertTrue(file.exists())
        self.assertGreater(summary["planned"], 0)
        self.assertEqual(summary["removed"], 0)

    def test_removes_contents_but_keeps_the_directory(self) -> None:
        self.put(".cache/uv/archive/file")
        self.put(".cache/uv/top-level-file")
        sibling = self.put(".cache/nvim/keep")
        self.run_clean(self.config(sysclean.Rule("uv", ".cache/uv", 2)))
        self.assertEqual(list((self.base / ".cache/uv").iterdir()), [])
        self.assertTrue(sibling.exists())

    def test_hostile_file_names_are_only_data(self) -> None:
        for name in HOSTILE_NAMES:
            self.put(f".cache/uv/{name}/{name}")
        keep = self.put(".cache/keep")
        self.run_clean(self.config(sysclean.Rule("uv", ".cache/uv", 2)))
        self.assertEqual(list((self.base / ".cache/uv").iterdir()), [])
        self.assertTrue(keep.exists())
        self.assertFalse(Path("PWNED").exists())
        self.assertEqual(list(self.base.rglob("PWNED")), [])

    def test_age_limit_keeps_recent_entries(self) -> None:
        old = self.put(".cache/yay/old-package/file", age_days=60)
        new = self.put(".cache/yay/new-package/file", age_days=2)
        rule = sysclean.Rule("yay", ".cache/yay", 1, min_age_days=30)
        self.run_clean(self.config(rule))
        self.assertFalse(old.exists())
        self.assertTrue(new.exists())

    def test_age_uses_the_newest_file_inside(self) -> None:
        self.put(".cache/yay/mixed/old", age_days=60)
        recent = self.put(".cache/yay/mixed/new")
        self.run_clean(self.config(sysclean.Rule("yay", ".cache/yay", 1, min_age_days=30)))
        self.assertTrue(recent.exists())

    def test_higher_levels_are_left_alone(self) -> None:
        one = self.put(".cache/one/file")
        two = self.put(".cache/two/file")
        self.run_clean(self.config(sysclean.Rule("one", ".cache/one", 1), sysclean.Rule("two", ".cache/two", 2)), level=1)
        self.assertFalse(one.exists())
        self.assertTrue(two.exists())

    def test_busy_target_is_skipped_and_reported(self) -> None:
        file = self.put(".cache/uv/open-file")
        with file.open():
            summary = self.run_clean(self.config(sysclean.Rule("uv", ".cache/uv", 2)))
        self.assertTrue(file.exists())
        self.assertIn("in use", summary["skipped"][0])

    def test_running_program_blocks_its_rule(self) -> None:
        file = self.put(".cache/mozilla/file")
        with patch.object(guard, "running_commands", return_value={"firefox"}):
            summary = self.run_clean(self.config(sysclean.Rule("ff", ".cache/mozilla", 2, blocked_by=("firefox",))))
        self.assertTrue(file.exists())
        self.assertIn("running: firefox", summary["skipped"][0])

    def test_level_three_is_never_applied_without_a_terminal(self) -> None:
        file = self.put(".oldapp/file")
        with patch("sys.stdin.isatty", return_value=False):
            summary = self.run_clean(self.config(sysclean.Rule("old", ".oldapp", 3, whole=True)))
        self.assertTrue(file.exists())
        self.assertIn("not confirmed", summary["skipped"][0])

    def test_level_three_removes_only_what_was_confirmed(self) -> None:
        yes = self.put(".yes/file")
        no = self.put(".no/file")
        rules = (sysclean.Rule("yes", ".yes", 3, whole=True), sysclean.Rule("no", ".no", 3, whole=True))
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=["y", "n"]):
            self.run_clean(self.config(*rules))
        self.assertFalse(yes.parent.exists())
        self.assertTrue(no.exists())

    def test_missing_targets_and_missing_docker_do_not_stop_the_run(self) -> None:
        file = self.put(".cache/here/file")
        summary = self.run_clean(self.config(sysclean.Rule("gone", ".cache/gone", 1), sysclean.Rule("here", ".cache/here", 1)))
        self.assertFalse(file.exists())
        self.assertEqual(summary["failed"], [])
        self.assertIn("Docker", summary["skipped"][0])

    def test_failed_removal_is_reported(self) -> None:
        self.put(".cache/uv/file")
        with patch.object(guard, "remove", side_effect=OSError("denied")):
            summary = self.run_clean(self.config(sysclean.Rule("uv", ".cache/uv", 2)))
        self.assertEqual(len(summary["failed"]), 1)

    def test_rule_from_config_cannot_reach_protected_paths(self) -> None:
        key = self.put(".ssh/id_key")
        summary = self.run_clean(self.config(sysclean.Rule("bad", ".ssh", 3, whole=True)))
        self.assertTrue(key.exists())
        self.assertIn("protected", summary["skipped"][0])


class ConfigTest(TempHome):
    def write(self, text: str) -> Path:
        path = self.base / "local.toml"
        path.write_text(text)
        return path

    def test_defaults_when_there_is_no_file(self) -> None:
        config = sysclean.load_config(self.base / "missing.toml")
        self.assertEqual((config.warn_gb, config.critical_gb, config.age_days), (30, 10, 30))
        self.assertIn("my/php:*", config.protected_images)

    def test_local_settings_add_to_the_defaults(self) -> None:
        config = sysclean.load_config(self.write(
            'age_days = 14\n[docker]\nprotected = ["mine:*"]\n'
            '[[rules]]\nlevel = 2\npath = "Work/a/cache"\n'
            '[worktrees.repos]\n"/repo" = "owner/name"\n'
        ))
        self.assertEqual(config.age_days, 14)
        self.assertIn("my/php:*", config.protected_images)
        self.assertIn("mine:*", config.protected_images)
        self.assertEqual(config.rules[-1].path, "Work/a/cache")
        self.assertEqual(config.repos["/repo"], "owner/name")

    def test_broken_config_stops_with_a_clear_error(self) -> None:
        for text in ("not toml [", "[[rules]]\nlevel = 9\npath = 'x'\n", "[[rules]]\nlevel = 1\n"):
            with self.subTest(text=text), self.assertRaises(ToolError):
                sysclean.load_config(self.write(text))


class DockerTest(unittest.TestCase):
    now = datetime.now(timezone.utc)

    def image(self, name: str, *tags: str, age: int = 60) -> docker.Image:
        return docker.Image(f"sha256:{name}", tags, 100, self.now - timedelta(days=age))

    def pick(self, images, used=(), protected=sysclean.PROTECTED_IMAGES, tagged=False, age=30):
        return docker.candidates(images, set(used), protected, tagged=tagged, now=self.now, min_age_days=age)

    def test_dangling_needs_no_tag_and_enough_age(self) -> None:
        old, new, tagged = self.image("a"), self.image("b", age=1), self.image("c", "x:1")
        self.assertEqual(self.pick([old, new, tagged]), [old])

    def test_unknown_age_is_skipped(self) -> None:
        self.assertEqual(self.pick([docker.Image("sha256:a", (), 1, None)]), [])

    def test_images_used_by_any_container_are_kept(self) -> None:
        image = self.image("a")
        self.assertEqual(self.pick([image], used=[image.id]), [])

    def test_php_images_are_always_protected(self) -> None:
        protected = [self.image("a", "my/php:8.4-dev"), self.image("b", "php:8.4-cli"), self.image("c", "my/php:7.4-dev", "other:1")]
        self.assertEqual(self.pick(protected, tagged=True, age=0), [])

    def test_removal_uses_plain_rmi_with_exact_references(self) -> None:
        calls = []

        def fake(*args, **kwargs):
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, "", "")

        with patch.object(docker, "_docker", fake):
            docker.remove_image(self.image("abc"))
            docker.remove_image(self.image("def", "app:1", "app:2"))
        self.assertEqual(calls, [("rmi", "sha256:abc"), ("rmi", "app:1"), ("rmi", "app:2")])

    def test_source_never_prunes_or_forces(self) -> None:
        source = Path(docker.__file__).read_text() + Path(sysclean.__file__).read_text()
        for banned in ('"prune"', '"-f"', '"--force"', '"-a"', "shell=True", '"volume", "rm"'):
            self.assertNotIn(banned, source.replace('"pnpm", "store", "prune"', ""))

    def test_docker_failure_skips_docker_rules_only(self) -> None:
        config = sysclean.Config()
        with (
            patch.object(docker, "available", return_value=True),
            patch.object(docker, "images", side_effect=ToolError("boom")),
        ):
            self.assertEqual(sysclean.docker_images(3, config), ([], [], "boom"))


class WatchTest(TempHome):
    def setUp(self) -> None:
        super().setUp()
        self.posts = []
        post = patch.object(sysclean.notify, "post", lambda *args, **kwargs: self.posts.append((args, kwargs)) or True)
        post.start()
        self.addCleanup(post.stop)
        plans = patch.object(sysclean, "plan_rules", return_value=[])
        plans.start()
        self.addCleanup(plans.stop)

    def check(self, free_gib: float) -> None:
        fake = type("Usage", (), {"free": int(free_gib * GIB)})
        with patch.object(sysclean.shutil, "disk_usage", return_value=fake), patch("builtins.print"):
            sysclean.watch(sysclean.Config())

    def test_levels(self) -> None:
        config = sysclean.Config()
        self.assertEqual(sysclean.disk_level(40 * GIB, config), "ok")
        self.assertEqual(sysclean.disk_level(20 * GIB, config), "warning")
        self.assertEqual(sysclean.disk_level(5 * GIB, config), "critical")

    def test_quiet_when_there_is_plenty_of_space(self) -> None:
        self.check(100)
        self.assertEqual(self.posts, [])

    def test_notifies_once_per_crossing(self) -> None:
        self.check(20)
        self.check(19)
        self.check(18)
        self.assertEqual(len(self.posts), 1)
        self.assertEqual(self.posts[0][1]["key"], "sysclean-low-disk")

    def test_getting_worse_notifies_again_with_critical_urgency(self) -> None:
        self.check(20)
        self.check(5)
        self.assertEqual(len(self.posts), 2)
        self.assertEqual(self.posts[1][1]["urgency"], "critical")

    def test_recovering_rearms_the_warning(self) -> None:
        self.check(20)
        self.check(100)
        self.check(20)
        self.assertEqual(len(self.posts), 2)

    def test_watch_never_removes_anything(self) -> None:
        with patch.object(guard, "remove") as remove:
            self.check(1)
        remove.assert_not_called()

    def test_corrupt_state_is_treated_as_ok(self) -> None:
        state = sysclean.watch_state_file()
        state.parent.mkdir(parents=True)
        state.write_text("not json")
        self.check(20)
        self.assertEqual(len(self.posts), 1)


class SummaryTest(unittest.TestCase):
    def post(self, summary: dict, apply: bool):
        with patch.object(sysclean.notify, "post") as post:
            sysclean.post_summary({"planned": GIB, "freed": GIB, "skipped": [], "failed": [], **summary}, 1, apply)
        return post.call_args

    def test_preview_says_nothing_was_removed(self) -> None:
        self.assertIn("Nothing was removed", self.post({}, False).args[2])

    def test_stays_quiet_when_there_is_nothing_to_do(self) -> None:
        self.assertIsNone(self.post({"planned": 0}, False))

    def test_failure_is_critical(self) -> None:
        self.assertEqual(self.post({"failed": ["x"]}, True).kwargs["urgency"], "critical")


class ClassifyTest(unittest.TestCase):
    def tree(self, **fields) -> worktrees.Worktree:
        return worktrees.Worktree(Path("/w"), **{"merged": True, **fields})

    def test_merged_and_clean_is_safe(self) -> None:
        self.assertEqual(worktrees.classify(self.tree()), "safe")

    def test_keep_reasons_win_over_merged(self) -> None:
        cases = {
            "in-use": {"in_use": True},
            "open-pr": {"pr": "OPEN"},
            "unpushed": {"unpushed": 1},
            "uncommitted": {"uncommitted": ["a.php"]},
            "recent-session": {"session_days": 1.0},
            "env-differs": {"env_differs": [".env"]},
            "unmerged": {"merged": False},
        }
        for status, fields in cases.items():
            with self.subTest(status=status):
                self.assertEqual(worktrees.classify(self.tree(**fields)), status)

    def test_a_failed_check_is_never_safe(self) -> None:
        self.assertEqual(worktrees.classify(self.tree(failed=["status"])), "unknown")
        self.assertEqual(worktrees.classify(self.tree(pr="unknown")), "unknown")

    def test_old_session_does_not_block(self) -> None:
        self.assertEqual(worktrees.classify(self.tree(session_days=30.0)), "safe")

    def test_slug_parsing(self) -> None:
        self.assertEqual(worktrees.repo_slug("git@github.com:owner/repo.git"), "owner/repo")
        self.assertEqual(worktrees.repo_slug("https://github.com/owner/repo"), "owner/repo")
        self.assertIsNone(worktrees.repo_slug("alias:repo"))


class WorktreeAuditTest(TempHome):
    def git(self, path: Path, *args: str) -> str:
        env = {
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.test",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.test",
        }
        return subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True, text=True, env=env).stdout

    def setUp(self) -> None:
        super().setUp()
        self.origin = self.base / "origin.git"
        self.main = self.base / "Work" / "app"
        self.main.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], check=True)
        self.git(self.main, "init", "-q", "-b", "main")
        self.git(self.main, "remote", "add", "origin", str(self.origin))
        (self.main / ".gitignore").write_text(".env\nnode_modules/\n")
        (self.main / "app.txt").write_text("one\n")
        (self.main / ".env").write_text("APP_KEY=same\n")
        self.git(self.main, "add", ".gitignore", "app.txt")
        self.git(self.main, "commit", "-qm", "init")
        self.git(self.main, "push", "-q", "origin", "main")
        self.tree = self.base / "Work" / "tree"
        self.git(self.main, "worktree", "add", "-q", "-b", "feature", str(self.tree))
        (self.tree / ".env").write_text("APP_KEY=same\n")

    def status(self) -> worktrees.Worktree:
        pull_requests = patch.object(worktrees, "_pull_requests", return_value=[])
        with (
            pull_requests,
            patch.object(worktrees.process, "command_exists", return_value=True),
            patch.object(worktrees, "load_sessions", return_value=[]),
        ):
            found = worktrees.run_audit([self.base / "Work"], {str(self.main): "owner/app"})
        self.assertEqual([tree.path for tree in found], [self.tree])
        return found[0]

    def test_finds_only_linked_worktrees(self) -> None:
        self.assertEqual(worktrees.discover([self.base / "Work"]), [self.tree])

    def test_merged_clean_worktree_is_safe(self) -> None:
        self.assertEqual(self.status().status, "safe")

    def test_uncommitted_work_on_merged_base_is_kept(self) -> None:
        (self.tree / "app.txt").write_text("changed\n")
        tree = self.status()
        self.assertEqual(tree.status, "uncommitted")
        self.assertEqual(tree.uncommitted, ["app.txt"])

    def test_change_matching_upstream_does_not_block(self) -> None:
        (self.main / "app.txt").write_text("two\n")
        self.git(self.main, "add", "app.txt")
        self.git(self.main, "commit", "-qm", "two")
        self.git(self.main, "push", "-q", "origin", "main")
        (self.tree / "app.txt").write_text("two\n")
        self.assertEqual(self.status().uncommitted, [])

    def test_generated_folder_link_is_not_work(self) -> None:
        (self.tree / "node_modules").symlink_to(self.main)
        self.assertEqual(self.status().status, "safe")

    def test_unpushed_commit_is_kept(self) -> None:
        (self.tree / "new.txt").write_text("x\n")
        self.git(self.tree, "add", "new.txt")
        self.git(self.tree, "commit", "-qm", "work")
        tree = self.status()
        self.assertEqual(tree.status, "unpushed")
        self.assertEqual(tree.unpushed, 1)

    def test_ignored_files_are_seen_and_values_are_not_reported(self) -> None:
        (self.tree / ".env").write_text("APP_KEY=secret-value\n")
        tree = self.status()
        self.assertEqual(tree.status, "env-differs")
        self.assertEqual(tree.env_differs, [".env"])
        self.assertNotIn("secret-value", json.dumps(sysclean.tree_json(tree), default=str))

    def test_process_inside_marks_it_in_use(self) -> None:
        with patch.object(worktrees, "users_of", return_value={self.tree: {"php"}}):
            self.assertEqual(self.status().status, "in-use")

    def test_missing_pull_request_data_is_unknown(self) -> None:
        with patch.object(worktrees, "load_sessions", return_value=[]), patch.object(worktrees.process, "command_exists", return_value=False):
            found = worktrees.run_audit([self.base / "Work"], {})
        self.assertEqual(found[0].status, "unknown")

    def test_audit_changes_nothing(self) -> None:
        before = self.git(self.main, "worktree", "list", "--porcelain")
        self.status()
        self.assertEqual(self.git(self.main, "worktree", "list", "--porcelain"), before)
        self.assertTrue(self.tree.exists())

    def test_reclaimable_counts_hardlinks_only_when_all_links_go(self) -> None:
        store = self.put("store/blob")
        store.write_bytes(b"x" * 100000)
        first = self.base / "one"
        second = self.base / "two"
        first.mkdir()
        second.mkdir()
        os.link(store, first / "blob")
        os.link(store, second / "blob")
        self.assertLess(worktrees.reclaimable([first, second]), 90000)
        self.assertGreater(worktrees.reclaimable([first, second, store.parent]), 90000)


class CliTest(TempHome):
    def test_subcommands_ask_only_for_what_they_need(self) -> None:
        with patch.object(sysclean.process, "command_exists", return_value=False), patch("builtins.print"):
            with self.assertRaisesRegex(ToolError, "git"):
                sysclean.main(["worktrees"])
            with self.assertRaisesRegex(ToolError, "docker"):
                sysclean.main(["volumes"])

    def test_clean_defaults_to_a_preview_of_level_one(self) -> None:
        with patch.object(sysclean, "clean", return_value={"failed": []}) as clean, patch.object(sysclean.guard, "real_home", return_value=self.base):
            self.assertEqual(sysclean.main(["clean"]), 0)
        self.assertEqual(clean.call_args.args[:2], (1, False))

    def test_failed_clean_returns_an_error(self) -> None:
        with patch.object(sysclean, "clean", return_value={"failed": ["x"]}), patch.object(sysclean.guard, "real_home", return_value=self.base):
            self.assertEqual(sysclean.main(["clean", "--apply"]), 1)


if __name__ == "__main__":
    unittest.main()
