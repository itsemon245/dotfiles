from __future__ import annotations

import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotfiles_tools import env_replace
from dotfiles_tools.cli import ToolError

REAL_HOME = Path(os.path.realpath(Path.home()))


class TempHome(unittest.TestCase):
    """Every test works in a throwaway home. Real projects are never reachable."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(os.path.realpath(temp.name))
        self.assertTrue(self.base.is_relative_to(os.path.realpath(tempfile.gettempdir())))
        self.assertFalse(self.base.is_relative_to(REAL_HOME / "Work"))
        env = patch.dict(os.environ, {"HOME": str(self.base), "XDG_STATE_HOME": str(self.base / "state")})
        env.start()
        self.addCleanup(env.stop)
        self.assertEqual(env_replace.backup_root(), self.base / "state/dotfiles/backups/env-replace")
        (self.base / "Work").mkdir()

    def put(self, relative: str, text: str) -> Path:
        path = self.base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode())
        return path

    def run_tool(self, *argv: str) -> str:
        lines: list[str] = []
        with patch("builtins.print", lambda *parts, **_: lines.append(" ".join(map(str, parts)))):
            env_replace.main(list(argv))
        return "\n".join(lines)

    def git(self, cwd: Path, *args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "-c", "init.defaultBranch=main", *args],
            cwd=cwd,
            check=True,
            capture_output=True,
        )


class DiscoveryTest(TempHome):
    def test_finds_env_variants_and_skips_templates_and_dependencies(self) -> None:
        keep = [self.put("Work/a/.env", "K=1\n"), self.put("Work/a/.env.local", "K=1\n"), self.put("Work/b/sub/.env.testing", "K=1\n")]
        for skipped in ("Work/a/.env.example", "Work/a/.env.bak", "Work/a/node_modules/x/.env", "Work/a/vendor/y/.env", "Work/a/env", "Work/a/.envrc"):
            self.put(skipped, "K=1\n")
        self.assertEqual(env_replace.discover([self.base / "Work"]), sorted(keep))

    def test_finds_worktrees_outside_the_roots(self) -> None:
        repo = self.base / "Work/app"
        repo.mkdir()
        self.git(repo, "init")
        self.git(repo, "commit", "--allow-empty", "-m", "init")
        outside = self.base / "elsewhere/app-feature"
        self.git(repo, "worktree", "add", "-b", "feature", str(outside))
        self.put("Work/app/.env", "K=1\n")
        stray = self.put("elsewhere/app-feature/.env", "K=1\n")
        unrelated = self.put("elsewhere/other/.env", "K=1\n")
        found = env_replace.discover([self.base / "Work"])
        self.assertIn(stray, found)
        self.assertNotIn(unrelated, found)

    def test_symlinked_env_is_listed_once(self) -> None:
        target = self.put("Work/shared/.env", "K=1\n")
        (self.base / "Work/app").mkdir()
        (self.base / "Work/app/.env").symlink_to(target)
        self.assertEqual(env_replace.discover([self.base / "Work"]), [target])


class ReplaceTest(TempHome):
    def test_preview_changes_nothing(self) -> None:
        path = self.put("Work/a/.env", "DB_HOST=old\n")
        output = self.run_tool("DB_HOST", "new")
        self.assertEqual(path.read_text(), "DB_HOST=old\n")
        self.assertIn("would update", output)
        self.assertNotIn("old", output.replace("would", ""))  # value is masked
        self.assertFalse((self.base / "state").exists())

    def test_apply_replaces_only_the_exact_key(self) -> None:
        path = self.put(
            "Work/a/.env",
            "# DB_HOST=commented\nDB_HOST=old\nDB_HOST_READ=keep\nexport DB_HOST=old2\n  DB_HOST = spaced\nXDB_HOST=keep\n",
        )
        self.run_tool("DB_HOST", "new", "--apply")
        self.assertEqual(
            path.read_text(),
            "# DB_HOST=commented\nDB_HOST=new\nDB_HOST_READ=keep\nexport DB_HOST=new\n  DB_HOST = new\nXDB_HOST=keep\n",
        )

    def test_value_is_written_literally(self) -> None:
        for value in ["$(touch PWNED)", "a&b\\c/d", '"quoted value"', "`x`", "", "#hash"]:
            path = self.put("Work/a/.env", "K=old\n")
            self.run_tool("K", value, "--apply")
            self.assertEqual(path.read_text(), f"K={value}\n")
        self.assertFalse((self.base / "Work/a/PWNED").exists())

    def test_preserves_crlf_permissions_symlinks_and_missing_newline(self) -> None:
        target = self.put("Work/shared/.env", "A=1\r\nK=old\r\nB=2")
        target.chmod(0o600)
        link = self.base / "Work/app/.env"
        link.parent.mkdir()
        link.symlink_to(target)
        self.put("Work/other/.env", "K=old")
        self.run_tool("K", "new", "--apply")
        self.assertTrue(link.is_symlink())
        self.assertEqual(target.read_bytes(), b"A=1\r\nK=new\r\nB=2")
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
        self.assertEqual((self.base / "Work/other/.env").read_text(), "K=new")

    def test_backs_up_before_writing(self) -> None:
        path = self.put("Work/a/.env", "K=old\n")
        self.run_tool("K", "new", "--apply")
        backups = list(env_replace.backup_root().rglob(".env"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), "K=old\n")
        self.assertTrue(str(backups[0]).endswith(str(path)))

    def test_unchanged_files_are_not_rewritten(self) -> None:
        path = self.put("Work/a/.env", "K=same\n")
        before = path.stat().st_mtime_ns
        output = self.run_tool("K", "same", "--apply")
        self.assertIn("unchanged", output)
        self.assertEqual(path.stat().st_mtime_ns, before)
        self.assertFalse(env_replace.backup_root().exists())

    def test_file_filter_leaves_other_env_files_alone(self) -> None:
        local = self.put("Work/a/.env", "K=old\n")
        production = self.put("Work/a/.env.production", "K=old\n")
        self.run_tool("K", "new", "--apply", "--file", ".env")
        self.assertEqual(local.read_text(), "K=new\n")
        self.assertEqual(production.read_text(), "K=old\n")

    def test_list_mode_is_read_only(self) -> None:
        path = self.put("Work/a/.env", "K=secret\n")
        output = self.run_tool("K", "--show-values")
        self.assertIn("K=secret", output)
        self.assertEqual(path.read_text(), "K=secret\n")

    def test_rejects_bad_input(self) -> None:
        for argv in (["BAD KEY", "x"], ["K", "two\nlines"], ["K", "--apply"], ["K", "x", "--root", str(self.base / "missing")]):
            with self.subTest(argv=argv), self.assertRaises(ToolError):
                self.run_tool(*argv)


if __name__ == "__main__":
    unittest.main()
