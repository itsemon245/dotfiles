"""Hyprland startup orchestration."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from . import notify, process
from .paths import home, xdg_cache_home


class Startup:
    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self.log_dir = xdg_cache_home() / "hypr"
        self.log_file = self.log_dir / "startup.log"
        self.title = "Hyprland startup"
        self.default_wallpaper = Path(os.environ.get("DEFAULT_WALLPAPER", str(home() / "Wallpapers" / "default.png"))).expanduser()
        self.openrgb_script = Path(os.environ.get("OPENRGB_SCRIPT", str(home() / ".config/OpenRGB/scripts/wallust-colors.sh"))).expanduser()
        self.polkit_agent = Path(os.environ.get("POLKIT_AGENT", "/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1"))
        self.openwhispr_bin = Path(os.environ.get("OPENWHISPR_BIN", "/opt/openwhispr/open-whispr"))
        self.ibus_wayland_panel = Path(os.environ.get("IBUS_WAYLAND_PANEL", "/usr/lib/ibus/ibus-ui-gtk3"))

    def setup_log(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        if self.dry_run:
            print(f"+ truncate {self.log_file}")
        else:
            self.log_file.write_text("", encoding="utf-8")

    def log(self, message: str) -> None:
        line = f"[{datetime.now():%F %T}] [INFO] {message}"
        if self.dry_run:
            print(line)
            return
        with self.log_file.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def notify(self, message: str, urgency: str = "normal") -> None:
        notify.notify(self.title, message, urgency=urgency, dry_run=self.dry_run)

    def have(self, command: str, label: str) -> bool:
        if process.command_exists(command):
            return True
        self.log(f"Skipped {label}: missing command '{command}'.")
        self.notify(f"Skipped {label}: missing command '{command}'.", "critical")
        return False

    def run_logged(self, label: str, command: list[str]) -> bool:
        if not self.have(command[0], label):
            return False
        self.log(f"Running {label}: {process.printable(command)}")
        completed = process.run(command, dry_run=self.dry_run, log_file=self.log_file)
        if completed.returncode != 0:
            self.notify(f"{label} failed. See {self.log_file}.", "critical")
            return False
        return True

    def spawn(self, label: str, process_name: str, command: list[str]) -> None:
        if not self.have(command[0], label):
            return
        if process.pgrep("-x", process_name):
            self.log(f"{label} already running; skipping.")
            return
        self.log(f"Starting {label}: {process.printable(command)}")
        process.background(command, dry_run=self.dry_run, log_file=self.log_file)

    def spawn_path(self, label: str, path: Path, *args: str) -> None:
        if not path.is_file() or not os.access(path, os.X_OK):
            self.log(f"Skipped {label}: executable not found at {path}.")
            self.notify(f"Skipped {label}: executable not found at {path}.", "critical")
            return
        if process.pgrep("-f", str(path)):
            self.log(f"{label} already running; skipping.")
            return
        command = [str(path), *args]
        self.log(f"Starting {label}: {process.printable(command)}")
        process.background(command, dry_run=self.dry_run, log_file=self.log_file)

    def start_dunst(self) -> None:
        if not self.have("dunst", "notification daemon"):
            return
        if process.pgrep("-x", "dunst"):
            return
        self.log("Starting notification daemon: dunst")
        process.background(["dunst"], dry_run=self.dry_run, log_file=self.log_file)
        if not self.dry_run:
            time.sleep(0.3)

    def set_wallpaper(self) -> None:
        if not self.have("awww-daemon", "wallpaper daemon"):
            return
        if not self.have("awww", "wallpaper"):
            return
        self.spawn("wallpaper daemon", "awww-daemon", ["awww-daemon"])
        if not self.dry_run:
            time.sleep(0.3)
        if self.default_wallpaper.is_file():
            self.run_logged("wallpaper", ["awww", "img", str(self.default_wallpaper)])
        else:
            self.notify(f"Skipped wallpaper: missing file {self.default_wallpaper}.", "critical")

    def start_ibus(self) -> None:
        if not self.have("ibus", "IBus"):
            return
        os.environ["GTK_IM_MODULE"] = "ibus"
        os.environ["QT_IM_MODULE"] = "ibus"
        os.environ["XMODIFIERS"] = "@im=ibus"

        if not self.ibus_wayland_panel.is_file() or not os.access(self.ibus_wayland_panel, os.X_OK):
            self.notify(f"Skipped IBus Wayland panel: executable not found at {self.ibus_wayland_panel}.", "critical")
            return

        if process.pgrep("-x", "ibus-ui-gtk3"):
            self.log("IBus Wayland panel already running; skipping.")
        else:
            command = [
                str(self.ibus_wayland_panel),
                "--enable-wayland-im",
                "--exec-daemon",
                "--daemon-args",
                "--xim --panel disable",
            ]
            env = os.environ.copy()
            env.pop("GTK_IM_MODULE", None)
            env.pop("QT_IM_MODULE", None)
            self.log(f"Starting IBus Wayland panel: {process.printable(command)}")
            process.background(command, env=env, dry_run=self.dry_run, log_file=self.log_file)

        for _ in range(30):
            if self.dry_run:
                print("+ ibus list-engine")
                return
            completed = process.run(["ibus", "list-engine"], capture=True)
            if completed.returncode == 0:
                self.log("IBus daemon is ready.")
                return
            time.sleep(0.1)
        self.notify(f"IBus daemon did not become ready. See {self.log_file}.", "critical")

    def sync_openrgb_theme(self) -> None:
        if not self.openrgb_script.is_file():
            self.notify(f"Skipped OpenRGB theme sync: missing script {self.openrgb_script}.")
            return
        if self.have("openrgb", "OpenRGB theme sync"):
            self.run_logged("OpenRGB theme sync", ["bash", str(self.openrgb_script)])

    def move_window_later(self, label: str, workspace: str, delay: float, selectors: list[str]) -> None:
        if not self.have("hyprctl", f"{label} window move"):
            return
        code = r"""
import subprocess
import sys
import time
from pathlib import Path

label, workspace, delay, log_file, *selectors = sys.argv[1:]
time.sleep(float(delay))
for selector in selectors:
    with Path(log_file).open("ab") as handle:
        result = subprocess.run(
            ["hyprctl", "dispatch", "movetoworkspacesilent", f"{workspace},{selector}"],
            stdout=handle,
            stderr=subprocess.STDOUT,
        )
    if result.returncode == 0:
        with Path(log_file).open("a", encoding="utf-8") as handle:
            handle.write(f"Moved {label} window to {workspace}.\n")
        sys.exit(0)
with Path(log_file).open("a", encoding="utf-8") as handle:
    handle.write(f"Could not find {label} window to move.\n")
"""
        command = [
            sys.executable,
            "-c",
            code,
            label,
            workspace,
            str(delay),
            str(self.log_file),
            *selectors,
        ]
        process.background(command, dry_run=self.dry_run)

    def run(self) -> int:
        self.setup_log()
        self.start_dunst()
        self.spawn_path("polkit authentication agent", self.polkit_agent)
        self.set_wallpaper()
        self.spawn("NetworkManager applet", "nm-applet", ["nm-applet", "--indicator"])
        self.spawn("Waybar", "waybar", ["waybar"])
        if not self.dry_run:
            time.sleep(1)
        self.start_ibus()
        self.sync_openrgb_theme()
        self.spawn("Slack", "slack", ["slack", "-u"])
        self.spawn("LocalSend", "localsend", ["localsend"])
        self.move_window_later(
            "LocalSend",
            "special:magic",
            3,
            [
                "class:^(localsend|LocalSend|localsend_app)$",
                "title:^(LocalSend)$",
            ],
        )
        self.spawn_path("OpenWhispr", self.openwhispr_bin, "--no-sandbox")
        return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hypr-startup", description="Start optional Hyprland desktop services.")
    parser.add_argument("--dry-run", action="store_true", help="print intended actions without starting services")
    args = parser.parse_args(argv)
    return Startup(dry_run=args.dry_run).run()
