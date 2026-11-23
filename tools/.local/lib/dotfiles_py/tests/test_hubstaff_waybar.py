from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotfiles_tools import hubstaff_waybar


class RenderTest(unittest.TestCase):
    def test_tracking_shows_hours_and_minutes(self) -> None:
        out = hubstaff_waybar.render({"active_project": {"name": "Support", "tracked_today": "2:43:14"}, "tracking": True})
        self.assertEqual(out["class"], ["tracking", "bg-dark"])
        self.assertTrue(out["text"].endswith(" 2:43:14"))
        self.assertIn("Tracking: Support", out["tooltip"])
        self.assertIn("2:43:14", out["tooltip"])

    def test_local_seconds_are_added_only_while_tracking(self) -> None:
        tracking = {"active_project": {"name": "S", "tracked_today": "2:59:58"}, "tracking": True}
        self.assertTrue(hubstaff_waybar.render(tracking, 3)["text"].endswith(" 3:00:01"))
        stopped = dict(tracking, tracking=False)
        self.assertTrue(hubstaff_waybar.render(stopped, 3)["text"].endswith(" 2:59:58"))

    def test_stopped(self) -> None:
        out = hubstaff_waybar.render({"active_project": {"name": "Support", "tracked_today": "0:05:00"}, "tracking": False})
        self.assertEqual(out["class"], ["stopped", "bg-dark"])
        self.assertIn("resume", out["tooltip"])

    def test_tone_class_follows_the_wallpaper(self) -> None:
        status = {"active_project": {"name": "S", "tracked_today": "0:01:00"}, "tracking": True}
        self.assertEqual(hubstaff_waybar.render(status, tone="light")["class"], ["tracking", "bg-light"])

    def test_not_running_hides_the_module(self) -> None:
        self.assertEqual(hubstaff_waybar.render(None)["text"], "")

    def test_missing_cli_reads_as_not_running(self) -> None:
        with patch.dict(os.environ, {"HUBSTAFF_CLI": "/nonexistent/HubstaffCLI"}):
            self.assertIsNone(hubstaff_waybar.read_status())

    def test_durations(self) -> None:
        self.assertEqual(hubstaff_waybar.parse_duration("2:43:14"), 9794)
        self.assertIsNone(hubstaff_waybar.parse_duration("odd"))
        self.assertEqual(hubstaff_waybar.format_duration(9794), "2:43:14")
        self.assertEqual(hubstaff_waybar.format_duration(36005), "10:00:05")


if __name__ == "__main__":
    unittest.main()
