from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotfiles_tools import share_picker


class SharePickerTest(unittest.TestCase):
    """Runs main() against a fake picker that records each launch and prints a set answer."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="share-picker-test-"))
        self.launches = self.tmp / "launches"
        self.answer = self.tmp / "answer"
        fake = self.tmp / "fake-picker"
        fake.write_text(f'#!/bin/sh\necho x >> "{self.launches}"\ncat "{self.answer}"\n')
        fake.chmod(0o755)
        self.env = patch.dict(os.environ, {
            "XDG_RUNTIME_DIR": str(self.tmp),
            "XDPH_OUTPUT_SHARING_LIST": "DP-2:HKC G2421V",
            "XDPH_WINDOW_SHARING_LIST": "123[HC>]kitty[HT>]zsh[HE>]",
            "SHARE_PICKER_REUSE_SECONDS": "15",
        })
        self.env.start()
        self.picker = patch.object(share_picker, "REAL_PICKER", str(fake))
        self.picker.start()

    def tearDown(self) -> None:
        self.picker.stop()
        self.env.stop()
        assert self.tmp.name.startswith("share-picker-test-") and self.tmp.parent == Path(tempfile.gettempdir())
        shutil.rmtree(self.tmp)

    def pick(self, answer: str, *args: str) -> str:
        self.answer.write_text(answer + "\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            share_picker.main(list(args))
        return out.getvalue().strip()

    def launch_count(self) -> int:
        return len(self.launches.read_text().splitlines()) if self.launches.exists() else 0

    def test_repeat_requests_reuse_the_first_choice_without_showing_the_picker(self) -> None:
        self.assertEqual(self.pick("[SELECTION]r/screen:DP-2", "--allow-token"), "[SELECTION]r/screen:DP-2")
        for _ in range(3):
            self.assertEqual(self.pick("[SELECTION]/window:999", "--allow-token"), "[SELECTION]r/screen:DP-2")
        self.assertEqual(self.launch_count(), 1)

    def test_old_choice_is_not_reused(self) -> None:
        self.pick("[SELECTION]/screen:DP-2")
        data = json.loads(share_picker.cache_file().read_text())
        data["time"] = time.time() - 60
        share_picker.cache_file().write_text(json.dumps(data))
        self.assertEqual(self.pick("[SELECTION]/window:123"), "[SELECTION]/window:123")
        self.assertEqual(self.launch_count(), 2)

    def test_cancel_is_never_remembered(self) -> None:
        self.assertEqual(self.pick(""), "")
        self.pick("[SELECTION]/screen:DP-2")
        self.assertEqual(self.launch_count(), 2)

    def test_choice_is_not_reused_once_its_window_is_gone(self) -> None:
        self.pick("[SELECTION]/window:123")
        with patch.dict(os.environ, {"XDPH_WINDOW_SHARING_LIST": "456[HC>]chrome[HT>]x[HE>]"}):
            self.assertEqual(self.pick("[SELECTION]/window:456"), "[SELECTION]/window:456")
        self.assertEqual(self.launch_count(), 2)

    def test_remember_flag_is_dropped_when_the_app_cannot_restore(self) -> None:
        self.pick("[SELECTION]r/screen:DP-2", "--allow-token")
        self.assertEqual(self.pick("unused"), "[SELECTION]/screen:DP-2")

    def test_parse(self) -> None:
        self.assertEqual(share_picker.parse("[SELECTION]r/region:DP-2@0,0,100,100"), ("r", "region", "DP-2@0,0,100,100"))
        self.assertIsNone(share_picker.parse("[XDPH_PICKER_ERROR] boom"))
        self.assertIsNone(share_picker.parse("[SELECTION]r"))


if __name__ == "__main__":
    unittest.main()
