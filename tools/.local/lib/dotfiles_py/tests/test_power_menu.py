from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotfiles_tools.power_menu import ACTION_KEYS, command_for


class CommandForTest(unittest.TestCase):
    def test_reboot_and_shutdown_close_apps_first_with_hyprshutdown(self) -> None:
        self.assertEqual(
            command_for("reboot", has_hyprshutdown=True, uses_uwsm=False),
            ["hyprshutdown", "--post-cmd", "systemctl reboot"],
        )
        self.assertEqual(
            command_for("shutdown", has_hyprshutdown=True, uses_uwsm=False),
            ["hyprshutdown", "--post-cmd", "systemctl poweroff"],
        )

    def test_falls_back_to_systemctl_without_hyprshutdown_or_under_uwsm(self) -> None:
        for flags in ({"has_hyprshutdown": False, "uses_uwsm": False}, {"has_hyprshutdown": True, "uses_uwsm": True}):
            self.assertEqual(command_for("reboot", **flags), ["systemctl", "reboot"])

    def test_suspend_hibernate_and_lock_never_go_through_hyprshutdown(self) -> None:
        self.assertEqual(command_for("suspend", has_hyprshutdown=True, uses_uwsm=False), ["systemctl", "suspend"])
        self.assertEqual(command_for("hibernate", has_hyprshutdown=True, uses_uwsm=False), ["systemctl", "hibernate"])
        self.assertEqual(command_for("lock", has_hyprshutdown=True, uses_uwsm=False), ["loginctl", "lock-session"])

    def test_logout_is_handled_by_the_session_runtime(self) -> None:
        self.assertIsNone(command_for("logout", has_hyprshutdown=True, uses_uwsm=False))

    def test_menu_offers_all_six_actions(self) -> None:
        self.assertEqual(ACTION_KEYS, ("lock", "suspend", "hibernate", "logout", "reboot", "shutdown"))


if __name__ == "__main__":
    unittest.main()
