from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotfiles_tools import notify, notify_relay

HOSTILE = [
    "it's \"quoted\"",
    "back\\slash",
    "$(touch PWNED)",
    "`touch PWNED`",
    "<b>markup</b> & more",
    "line one\nline two",
    "-u critical",
    "--help",
    "; rm -rf nothing",
    "🧹 emoji",
]


class QueueCase(unittest.TestCase):
    """Every test runs against a throwaway state directory."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.state = Path(temp.name).resolve()
        env = patch.dict(os.environ, {"XDG_STATE_HOME": str(self.state)})
        env.start()
        self.addCleanup(env.stop)
        self.root = notify.queue_dir("inbox").parent
        self.assertTrue(self.root.is_relative_to(tempfile.gettempdir()))
        self.assertTrue(self.root.is_relative_to(self.state))
        self.inbox = self.root / "inbox"
        self.sent = self.root / "sent"
        self.rejected = self.root / "rejected"
        self.delivered: list[tuple[str, dict]] = []

        def fake_notify(title, message="", **kwargs):
            self.delivered.append((title, {"body": message, **kwargs}))
            return True

        for target, value in (
            ("dotfiles_tools.notify_relay.notify.notify", fake_notify),
            ("dotfiles_tools.notify_relay.notifier_ready", lambda: True),
        ):
            mock = patch(target, value)
            mock.start()
            self.addCleanup(mock.stop)

    def inbox_files(self) -> list[Path]:
        return sorted(self.inbox.glob("*"))

    def history(self, service: str) -> list[dict]:
        path = self.sent / f"{service}.jsonl"
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    def drop(self, name: str, content: str | bytes) -> Path:
        self.inbox.mkdir(parents=True, exist_ok=True)
        path = self.inbox / name
        path.write_bytes(content.encode() if isinstance(content, str) else content)
        return path


class PostTest(QueueCase):
    def test_writes_one_complete_message(self) -> None:
        self.assertTrue(notify.post("sysclean", "Done", "Freed 4G", icon="user-trash", key="weekly"))
        files = self.inbox_files()
        self.assertEqual(len(files), 1)
        message = json.loads(files[0].read_text(encoding="utf-8"))
        self.assertEqual(message["service"], "sysclean")
        self.assertEqual(message["title"], "Done")
        self.assertEqual(message["key"], "weekly")
        self.assertEqual(list((self.root / "tmp").iterdir()), [])

    def test_leaves_out_unused_optional_fields(self) -> None:
        notify.post("sysclean", "Done")
        message = json.loads(self.inbox_files()[0].read_text(encoding="utf-8"))
        self.assertEqual(set(message), {"service", "title"})

    def test_ttl_sets_a_timezone_aware_expiry(self) -> None:
        notify.post("sysclean", "Done", ttl=60)
        message = json.loads(self.inbox_files()[0].read_text(encoding="utf-8"))
        self.assertIsNotNone(datetime.fromisoformat(message["expires"]).tzinfo)

    def test_rejects_service_names_that_could_change_a_path(self) -> None:
        for service in ("../evil", "a/b", "", "UPPER", "-dash", "a b", ".hidden", "a\nb"):
            with self.subTest(service=service), patch("sys.stderr"):
                self.assertFalse(notify.post(service, "Title"))
        self.assertEqual(self.inbox_files(), [])

    def test_rejects_invalid_fields(self) -> None:
        cases = [
            {"title": ""},
            {"title": "   "},
            {"title": "x", "urgency": "panic"},
            {"title": "x", "icon": "-i"},
            {"title": "x", "key": "bad key"},
            {"title": "x", "body": "y" * (notify.MAX_BODY + 1)},
        ]
        for case in cases:
            with self.subTest(case=case), patch("sys.stderr"):
                self.assertFalse(notify.post("sysclean", **case))
        self.assertEqual(self.inbox_files(), [])

    def test_write_failure_returns_false_and_never_raises(self) -> None:
        self.state.joinpath("notify").write_text("a file where a directory should be")
        with patch("sys.stderr"):
            self.assertFalse(notify.post("sysclean", "Title"))

    def test_hostile_text_round_trips_without_side_effects(self) -> None:
        cwd = Path.cwd()
        for text in HOSTILE:
            self.assertTrue(notify.post("sysclean", text, text))
        notify_relay.drain()
        self.assertEqual([title for title, _ in self.delivered], HOSTILE)
        self.assertFalse((cwd / "PWNED").exists())
        self.assertEqual(self.inbox_files(), [])


class RelayTest(QueueCase):
    def test_delivers_oldest_first_and_records_history(self) -> None:
        notify.post("sysclean", "first", "one", urgency="critical", icon="dialog-warning", key="a")
        notify.post("backup", "second")
        self.assertTrue(notify_relay.drain())
        self.assertEqual([title for title, _ in self.delivered], ["first", "second"])
        options = self.delivered[0][1]
        self.assertEqual(options["urgency"], "critical")
        self.assertEqual(options["icon"], "dialog-warning")
        self.assertEqual(options["tag"], "a")
        self.assertTrue(options["escape"])
        self.assertEqual(self.inbox_files(), [])
        self.assertEqual(self.history("sysclean")[0]["status"], "delivered")
        self.assertEqual(self.history("backup")[0]["title"], "second")

    def test_critical_messages_stay_on_screen(self) -> None:
        notify.post("sysclean", "critical", urgency="critical")
        notify.post("sysclean", "normal")
        notify_relay.drain()
        self.assertEqual(self.delivered[0][1]["timeout"], 0)
        self.assertGreater(self.delivered[1][1]["timeout"], 0)

    def test_failed_delivery_keeps_the_message_and_retries(self) -> None:
        notify.post("sysclean", "one")
        notify.post("sysclean", "two")
        with patch("dotfiles_tools.notify_relay.notify.notify", return_value=False):
            self.assertFalse(notify_relay.drain())
        self.assertEqual(len(self.inbox_files()), 2)
        self.assertEqual(self.history("sysclean"), [])
        self.assertTrue(notify_relay.drain())
        self.assertEqual([title for title, _ in self.delivered], ["one", "two"])
        self.assertEqual(self.inbox_files(), [])

    def test_expired_messages_are_dropped_not_shown(self) -> None:
        past = (datetime.now().astimezone() - timedelta(hours=1)).isoformat()
        self.drop("1-sysclean-1.json", json.dumps({"service": "sysclean", "title": "old", "expires": past}))
        notify_relay.drain()
        self.assertEqual(self.delivered, [])
        self.assertEqual(self.history("sysclean")[0]["status"], "expired")
        self.assertEqual(self.inbox_files(), [])

    def test_future_expiry_is_delivered(self) -> None:
        notify.post("sysclean", "fresh", ttl=3600)
        notify_relay.drain()
        self.assertEqual(len(self.delivered), 1)

    def test_newest_message_wins_for_a_key(self) -> None:
        for text in ("10G left", "8G left", "5G left"):
            notify.post("sysclean", text, key="low-disk")
        notify.post("sysclean", "unrelated")
        notify_relay.drain()
        self.assertEqual([title for title, _ in self.delivered], ["5G left", "unrelated"])
        statuses = [entry["status"] for entry in self.history("sysclean")]
        self.assertEqual(statuses.count("replaced"), 2)

    def test_malformed_messages_are_set_aside(self) -> None:
        huge = json.dumps({"service": "sysclean", "title": "x" * (notify.MAX_MESSAGE_BYTES + 1)})
        bad = {
            "1-a.json": "{not json",
            "2-a.json": "[1, 2]",
            "3-a.json": json.dumps({"title": "no service"}),
            "4-a.json": json.dumps({"service": "../../evil", "title": "x"}),
            "5-a.json": json.dumps({"service": "ok", "title": "x", "expires": "tomorrow"}),
            "6-a.json": json.dumps({"service": "ok", "title": "x", "expires": "2020-01-01T00:00:00"}),
            "7-a.json": huge,
            "8-a.json": b"\xff\xfe bad utf8",
        }
        for name, content in bad.items():
            self.drop(name, content)
        notify.post("sysclean", "good")
        with patch("sys.stderr"):
            self.assertTrue(notify_relay.drain())
        self.assertEqual([title for title, _ in self.delivered], ["good"])
        self.assertEqual(sorted(path.name for path in self.rejected.iterdir()), sorted(bad))
        self.assertEqual(self.inbox_files(), [])
        self.assertFalse(self.state.parent.joinpath("evil.jsonl").exists())

    def test_symlinks_are_not_followed(self) -> None:
        secret = self.state / "secret.json"
        secret.write_text(json.dumps({"service": "ok", "title": "leak"}))
        self.inbox.mkdir(parents=True, exist_ok=True)
        (self.inbox / "1-a.json").symlink_to(secret)
        with patch("sys.stderr"):
            notify_relay.drain()
        self.assertEqual(self.delivered, [])
        self.assertTrue(secret.exists())
        self.assertTrue((self.rejected / "1-a.json").is_symlink())

    def test_messages_arriving_during_delivery_are_picked_up(self) -> None:
        notify.post("sysclean", "first")
        original = notify_relay.notify.notify

        def post_another(title, message="", **kwargs):
            if title == "first":
                notify.post("sysclean", "late")
            return original(title, message, **kwargs)

        with patch("dotfiles_tools.notify_relay.notify.notify", post_another):
            self.assertTrue(notify_relay.drain())
        self.assertEqual([title for title, _ in self.delivered], ["first", "late"])

    def test_two_relays_never_deliver_a_message_twice(self) -> None:
        for number in range(30):
            notify.post("sysclean", f"message {number}")
        threads = [threading.Thread(target=notify_relay.relay, args=(0,)) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(self.delivered), 30)
        self.assertEqual(len({title for title, _ in self.delivered}), 30)

    def test_writes_nothing_outside_its_own_directory(self) -> None:
        notify.post("sysclean", "contained")
        notify_relay.relay(0)
        self.assertEqual([path.name for path in self.state.iterdir()], ["notify"])
        self.assertTrue((self.root / "lock").exists())
        self.assertEqual(self.root.stat().st_mode & 0o777, 0o700)

    def test_no_notifier_leaves_the_inbox_alone(self) -> None:
        notify.post("sysclean", "waiting")
        with patch("dotfiles_tools.notify_relay.notifier_ready", return_value=False):
            self.assertEqual(notify_relay.relay(0), 0)
        self.assertEqual(self.delivered, [])
        self.assertEqual(len(self.inbox_files()), 1)

    def test_wait_gives_a_restarting_notifier_time_to_return(self) -> None:
        notify.post("sysclean", "waiting")
        answers = iter([False, False, True])
        with (
            patch("dotfiles_tools.notify_relay.notifier_ready", lambda: next(answers)),
            patch("dotfiles_tools.notify_relay.time.sleep"),
        ):
            notify_relay.relay(5)
        self.assertEqual(len(self.delivered), 1)

    def test_empty_inbox_does_not_wait_for_a_notifier(self) -> None:
        with (
            patch("dotfiles_tools.notify_relay.notifier_ready", return_value=False),
            patch("dotfiles_tools.notify_relay.time.sleep") as sleep,
        ):
            self.assertEqual(notify_relay.relay(15), 0)
        sleep.assert_not_called()

    def test_dry_run_changes_nothing(self) -> None:
        notify.post("sysclean", "pending")
        with patch("builtins.print") as output:
            self.assertEqual(notify_relay.main(["--dry-run"]), 0)
        self.assertIn("pending", str(output.call_args_list))
        self.assertEqual(self.delivered, [])
        self.assertEqual(len(self.inbox_files()), 1)


class PruneTest(QueueCase):
    def test_removes_only_old_history(self) -> None:
        now = datetime.now().astimezone()
        self.sent.mkdir(parents=True)
        old = {"title": "old", "handled_at": (now - timedelta(days=40)).isoformat()}
        new = {"title": "new", "handled_at": (now - timedelta(days=1)).isoformat()}
        path = self.sent / "sysclean.jsonl"
        path.write_text(json.dumps(old) + "\nnot json\n" + json.dumps(new) + "\n", encoding="utf-8")
        notify_relay.prune(now)
        lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("not json", lines)
        self.assertIn("new", lines[1])

    def test_removes_old_rejected_files_only(self) -> None:
        now = datetime.now().astimezone()
        self.rejected.mkdir(parents=True)
        old = self.rejected / "old.json"
        new = self.rejected / "new.json"
        old.write_text("x")
        new.write_text("x")
        stamp = (now - timedelta(days=40)).timestamp()
        os.utime(old, (stamp, stamp))
        notify_relay.prune(now)
        self.assertFalse(old.exists())
        self.assertTrue(new.exists())


class NotifierTest(unittest.TestCase):
    """Argument building for the real notifiers, with nothing actually sent."""

    def sent_args(self, available: set[str], *args, **kwargs) -> list[str]:
        with (
            patch("dotfiles_tools.notify.process.command_exists", lambda name: name in available),
            patch("dotfiles_tools.notify.process.run") as run,
        ):
            run.return_value = subprocess.CompletedProcess([], 0)
            notify.notify(*args, **kwargs)
        return [str(part) for part in run.call_args.args[0]]

    def test_title_cannot_be_read_as_an_option(self) -> None:
        for tool in ("dunstify", "notify-send"):
            args = self.sent_args({tool}, "-u critical", "--help")
            self.assertEqual(args[-3:], ["--", "-u critical", "--help"])

    def test_escape_protects_markup_only_when_requested(self) -> None:
        self.assertEqual(self.sent_args({"dunstify"}, "<a&b>", "x", escape=True)[-2], "&lt;a&amp;b&gt;")
        self.assertEqual(self.sent_args({"dunstify"}, "<b>hi</b>", "x")[-2], "<b>hi</b>")

    def test_tag_replaces_earlier_notifications(self) -> None:
        for tool in ("dunstify", "notify-send"):
            self.assertIn("string:x-dunst-stack-tag:low-disk", self.sent_args({tool}, "t", tag="low-disk"))

    def test_hyprctl_fallback_shows_plain_text(self) -> None:
        args = self.sent_args({"hyprctl"}, "a&b", "c", escape=True)
        self.assertEqual(args[-1], "a&b: c")

    def test_reports_success_and_failure(self) -> None:
        for code, expected in ((0, True), (1, False)):
            with (
                patch("dotfiles_tools.notify.process.command_exists", lambda name: name == "dunstify"),
                patch("dotfiles_tools.notify.process.run") as run,
            ):
                run.return_value = subprocess.CompletedProcess([], code)
                self.assertIs(notify.notify("t"), expected)

    def test_no_notifier_reports_failure(self) -> None:
        with patch("dotfiles_tools.notify.process.command_exists", return_value=False):
            self.assertFalse(notify.notify("t"))


class ReadinessTest(unittest.TestCase):
    def ready(self, available: set[str], owner: str = "b true\n", code: int = 0) -> bool:
        with (
            patch("dotfiles_tools.notify_relay.process.command_exists", lambda name: name in available),
            patch("dotfiles_tools.notify_relay.process.run") as run,
        ):
            run.return_value = subprocess.CompletedProcess([], code, owner, "")
            return notify_relay.notifier_ready()

    def test_ready_when_the_bus_name_has_an_owner(self) -> None:
        self.assertTrue(self.ready({"busctl", "dunstify"}))

    def test_not_ready_without_an_owner_so_dunst_is_not_activated(self) -> None:
        self.assertFalse(self.ready({"busctl", "dunstify"}, owner="b false\n"))

    def test_not_ready_when_the_bus_is_unreachable(self) -> None:
        self.assertFalse(self.ready({"busctl", "dunstify"}, owner="", code=1))

    def test_hyprctl_is_used_only_without_bus_notifiers(self) -> None:
        self.assertTrue(self.ready({"busctl", "hyprctl"}, owner="b false\n"))
        self.assertFalse(self.ready({"busctl", "hyprctl", "notify-send"}, owner="b false\n"))


if __name__ == "__main__":
    unittest.main()
