from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotfiles_tools import bt_autoconnect as bt

MAC = "AA:BB:CC:DD:EE:01"  # made-up address; this repo is public
INFO = """Device AA:BB:CC:DD:EE:01 (public)
	Name: Test Buds
	Icon: audio-headset
	Paired: yes
	Trusted: yes
	Connected: {connected}
	UUID: Audio Sink                (0000110b-0000-1000-8000-00805f9b34fb)
"""


def info(connected: str = "no", **changes: str) -> bt.DeviceInfo:
    text = INFO.format(connected=connected)
    for key, value in changes.items():
        text = text.replace(f"{key}: yes", f"{key}: {value}")
    return bt.parse_info(MAC, text)


class ParseTest(unittest.TestCase):
    def test_info(self) -> None:
        parsed = info()
        self.assertTrue(parsed.available and parsed.paired and parsed.trusted and parsed.audio)
        self.assertFalse(parsed.connected)

    def test_unknown_device_is_unavailable(self) -> None:
        self.assertFalse(bt.parse_info(MAC, f"Device {MAC} not available\n").available)

    def test_devices(self) -> None:
        self.assertEqual(bt.parse_devices(f"Device {MAC} Test Buds\nnoise\nDevice 11:22:33:44:55:66 X\n"),
                         [MAC, "11:22:33:44:55:66"])


class DecideTest(unittest.TestCase):
    def test_disconnected_trusted_audio_device_gets_connected(self) -> None:
        self.assertEqual(bt.decide(info(), bt.Memory(), now=0), "connect")

    def test_untrusted_or_non_audio_devices_are_left_alone(self) -> None:
        self.assertEqual(bt.decide(info(Trusted="no"), bt.Memory(), now=0), "wait")
        no_audio = info(); no_audio.audio = False
        self.assertEqual(bt.decide(no_audio, bt.Memory(), now=0), "wait")

    def test_a_disconnect_starts_a_cooldown_then_retries(self) -> None:
        memory = bt.Memory()
        self.assertEqual(bt.decide(info("yes"), memory, now=0), "wait")       # connected
        self.assertEqual(bt.decide(info(), memory, now=10), "wait")           # just disconnected
        self.assertEqual(bt.decide(info(), memory, now=10 + bt.COOLDOWN - 1), "wait")
        self.assertEqual(bt.decide(info(), memory, now=10 + bt.COOLDOWN), "connect")

    def test_never_connected_device_is_retried_every_pass(self) -> None:
        memory = bt.Memory()
        for now in (0, 30, 60):
            self.assertEqual(bt.decide(info(), memory, now=now), "connect")


if __name__ == "__main__":
    unittest.main()
