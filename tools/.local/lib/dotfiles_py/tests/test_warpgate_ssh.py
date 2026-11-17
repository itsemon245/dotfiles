from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from shutil import which
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotfiles_tools import warpgate_ssh
from dotfiles_tools.cli import ToolError

REAL_HOME = Path(os.path.realpath(Path.home()))

BASE = """
[gateway]
host = "gate.example.com"
port = 2222
user = "me"
identity_file = "~/.ssh/gate_key"

[vpn]
interface = "wt0"

[projects]
acme  = { name = "acmecorp", match = ["acme-corp"] }
shop  = {}

[banners]
prod  = { label = "PRODUCTION", color = "red" }
stage = { label = "STAGING", color = "orange" }
dev   = { label = "DEV", color = "orange" }
"""


class TempHome(unittest.TestCase):
    """Every test works in a throwaway home, so the real ~/.ssh is never reachable."""

    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(os.path.realpath(temp.name))
        self.assertFalse(self.base.is_relative_to(REAL_HOME))
        env = patch.dict(os.environ, {"HOME": str(self.base), "XDG_STATE_HOME": str(self.base / "state")})
        env.start()
        self.addCleanup(env.stop)
        self.assertEqual(warpgate_ssh.default_config_path(), self.base / ".ssh/warpgate/hosts.toml")

    def config(self, targets: list[str], overrides: str = "", extra: str = "") -> Path:
        path = warpgate_ssh.default_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        body = "".join(f'  "{name}",\n' for name in targets)
        path.write_text(BASE + extra + "\n[overrides]\n" + overrides + "\n[targets]\nall = [\n" + body + "]\n")
        return path

    def servers(self, targets: list[str], overrides: str = "", extra: str = ""):
        config = warpgate_ssh.load_config(self.config(targets, overrides, extra))
        return config, {s.target: s for s in warpgate_ssh.resolve(config)}

    def ssh_g(self, conf: Path, alias: str) -> dict[str, str]:
        if not which("ssh"):
            self.skipTest("ssh not installed")
        result = subprocess.run(["ssh", "-F", str(conf), "-G", alias], capture_output=True, text=True, stdin=subprocess.DEVNULL, check=True)
        return dict(line.split(" ", 1) for line in result.stdout.splitlines() if " " in line)


class DeriveTests(TempHome):
    def test_names_become_short_aliases(self) -> None:
        _, servers = self.servers(
            ["acme-corp-backend-01", "acme-corp-db-02", "acme-corp-backend-stage", "acme-corp-redis-stage",
             "ffmpeg-dev-acmecorp-01", "dev.acmecorp.ai", "shop-redis", "shop-worker-3", "bot-server"]
        )
        expected = {
            "acme-corp-backend-01": (("acme-prod1", "acmecorp-prod1"), "prod"),
            "acme-corp-db-02": (("acme-prod-db2", "acmecorp-prod-db2"), "prod"),
            "acme-corp-backend-stage": (("acme-stage", "acmecorp-stage"), "stage"),
            "acme-corp-redis-stage": (("acme-stage-redis", "acmecorp-stage-redis"), "stage"),
            "ffmpeg-dev-acmecorp-01": (("acme-dev-ffmpeg1", "acmecorp-dev-ffmpeg1"), "dev"),
            "dev.acmecorp.ai": (("acme-dev", "acmecorp-dev"), "dev"),
            "shop-redis": (("shop-prod-redis",), "prod"),
            "shop-worker-3": (("shop-prod-worker3",), "prod"),
            "bot-server": (("bot-server",), None),
        }
        for target, (aliases, env) in expected.items():
            with self.subTest(target=target):
                self.assertEqual(servers[target].aliases, aliases)
                self.assertEqual(servers[target].env, env)

    def test_overrides_set_alias_env_user_port_and_key(self) -> None:
        _, servers = self.servers(
            ["www.acmecorp.ai", "monitor.acmecorp.ai", "legacy-box", "shop-backend-01"],
            overrides='"www.acmecorp.ai" = { alias = "acme-prod" }\n'
            '"monitor.acmecorp.ai" = { env = "none" }\n'
            '"legacy-box" = { user = "deploy", port = 2223, identity_file = "~/.ssh/other" }\n'
            '"shop-backend-01" = { port = 2222 }\n',
        )
        self.assertEqual(servers["www.acmecorp.ai"].aliases, ("acme-prod", "acmecorp-prod"))
        self.assertEqual(servers["www.acmecorp.ai"].env, "prod")
        self.assertIsNone(servers["monitor.acmecorp.ai"].env)
        legacy = servers["legacy-box"]
        self.assertEqual((legacy.user, legacy.port, legacy.identity_file), ("deploy", 2223, "~/.ssh/other"))
        self.assertIsNone(servers["shop-backend-01"].port)  # same as the gateway, so not repeated

    def test_project_settings_apply_unless_overridden(self) -> None:
        extra = ""
        path = self.config(["other-backend-01", "other-db-01"], overrides='"other-db-01" = { user = "dba" }\n', extra=extra)
        path.write_text(path.read_text().replace("shop  = {}", 'shop  = {}\nother = { user = "ops", port = 2300 }'))
        servers = {s.target: s for s in warpgate_ssh.resolve(warpgate_ssh.load_config(path))}
        self.assertEqual((servers["other-backend-01"].user, servers["other-backend-01"].port), ("ops", 2300))
        self.assertEqual((servers["other-db-01"].user, servers["other-db-01"].port), ("dba", 2300))

    def test_groups_are_only_labels(self) -> None:
        path = warpgate_ssh.default_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(BASE + '\n[targets]\nfirst = ["shop-redis"]\nsecond = [\n  "acme-corp-backend-01",\n]\n')
        config = warpgate_ssh.load_config(path)
        self.assertEqual(config.targets, ("shop-redis", "acme-corp-backend-01"))


class ValidationTests(TempHome):
    def test_duplicate_alias_names_both_targets(self) -> None:
        with self.assertRaisesRegex(ToolError, "acme-corp-backend-01 and acme-corp-01 both become acme-prod1.*overrides"):
            self.servers(["acme-corp-backend-01", "acme-corp-01"])

    def test_duplicate_target(self) -> None:
        with self.assertRaisesRegex(ToolError, "listed twice"):
            self.servers(["shop-redis", "shop-redis"])

    def test_unknown_keys_are_rejected(self) -> None:
        with self.assertRaisesRegex(ToolError, "unknown key"):
            self.servers(["shop-redis"], overrides='"shop-redis" = { prot = 2223 }\n')
        with self.assertRaisesRegex(ToolError, "unknown key"):
            self.servers(["shop-redis"], extra='\n[rules]\ndefault_evn = "prod"\n')

    def test_override_for_an_unlisted_target(self) -> None:
        with self.assertRaisesRegex(ToolError, "not listed in \\[targets\\]: shop-reddis"):
            self.servers(["shop-redis"], overrides='"shop-reddis" = { env = "none" }\n')

    def test_settings_inside_the_target_lists_point_to_overrides(self) -> None:
        path = warpgate_ssh.default_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(BASE + '\n[targets]\nall = [{ target = "shop-redis", alias = "x" }]\n')
        with self.assertRaisesRegex(ToolError, "go in \\[overrides\\]"):
            warpgate_ssh.load_config(path)

    def test_bad_alias_characters(self) -> None:
        with self.assertRaisesRegex(ToolError, "may only use"):
            self.servers(["shop-redis"], overrides='"shop-redis" = { alias = "Shop_Redis" }\n')

    def test_clash_with_existing_ssh_config_host(self) -> None:
        config, servers = self.servers(["bot-server"])
        ssh_config = self.base / ".ssh/config"
        ssh_config.write_text("Include warpgate/*.conf\n\nHost bot-server other\n  HostName 10.0.0.1\nHost *\n  User x\n")
        with self.assertRaisesRegex(ToolError, "alias already used .*bot-server"):
            warpgate_ssh.check_collisions(config, list(servers.values()), ssh_config)


class RenderTests(TempHome):
    def render(self, targets: list[str], overrides: str = "") -> Path:
        config, servers = self.servers(targets, overrides)
        output = warpgate_ssh.default_output_path()
        output.write_text(warpgate_ssh.render(config, list(servers.values())))
        return output

    def test_rendered_config_resolves_in_ssh(self) -> None:
        output = self.render(["acme-corp-backend-01", "acme-corp-db-stage", "bot-server", "legacy-box"], '"legacy-box" = { port = 2223 }\n')
        prod = self.ssh_g(output, "acmecorp-prod1")
        self.assertEqual((prod["hostname"], prod["port"], prod["user"]), ("gate.example.com", "2222", "me:acme-corp-backend-01"))
        self.assertIn("PRODUCTION: %n", prod["localcommand"])
        self.assertEqual(prod["controlmaster"], "auto")
        self.assertIn("STAGING", self.ssh_g(output, "acme-stage-db")["localcommand"])
        self.assertIn("SERVER", self.ssh_g(output, "bot-server")["localcommand"])
        self.assertEqual(self.ssh_g(output, "legacy-box")["port"], "2223")

    def test_only_servers_the_shared_rules_get_wrong_have_their_own_banner(self) -> None:
        output = self.render(
            ["acme-corp-backend-01", "monitor.acmecorp.ai", "www.acmecorp.ai"],
            '"monitor.acmecorp.ai" = { env = "none" }\n"www.acmecorp.ai" = { alias = "acme-web" }\n',
        )
        block = {b.splitlines()[0]: b for b in output.read_text().split("\n\n") if b.startswith("Host ")}
        self.assertNotIn("LocalCommand", block["Host acme-prod1 acmecorp-prod1"])
        self.assertIn("SERVER", block["Host acme-prod-monitor acmecorp-prod-monitor"])  # env = "none" beats *-prod*
        self.assertIn("PRODUCTION", block["Host acme-web acmecorp-web"])  # alias names no env, target is prod
        for alias, label in (("acme-prod1", "PRODUCTION"), ("acmecorp-prod-monitor", "SERVER"), ("acme-web", "PRODUCTION")):
            with self.subTest(alias=alias):
                self.assertIn(f"{label}: %n", self.ssh_g(output, alias)["localcommand"])

    def test_banner_only_prints_to_a_terminal(self) -> None:
        output = self.render(["acme-corp-backend-01"])
        self.assertIn("test -t 1 && printf", self.ssh_g(output, "acme-prod1")["localcommand"])

    def test_vpn_down_fails_fast_with_the_warning(self) -> None:
        output = self.render(["acme-corp-backend-01"])
        output.write_text(output.read_text().replace("/sys/class/net/wt0", "/sys/class/net/wt-test-missing"))
        if not which("ssh"):
            self.skipTest("ssh not installed")
        # ControlPath=none: ssh expands ~ from the password database, not $HOME, so keep sockets out of the real ~/.ssh
        result = subprocess.run(
            ["ssh", "-F", str(output), "-o", "ControlPath=none", "acme-prod1", "true"],
            capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=20,
        )
        self.assertEqual(result.returncode, 255)
        self.assertIn("NetBird VPN is not connected", result.stderr)
        self.assertNotIn("Connection closed", result.stderr)
        up = self.render(["acme-corp-backend-01"])
        up.write_text(up.read_text().replace("/sys/class/net/wt0", "/sys/class/net/lo"))  # lo always exists
        self.assertNotIn("proxycommand", self.ssh_g(up, "acme-prod1"))

    def test_prefix_is_added_to_every_alias(self) -> None:
        path = self.config(["acme-corp-backend-01"])
        path.write_text(path.read_text().replace('identity_file = "~/.ssh/gate_key"', 'identity_file = "~/.ssh/gate_key"\nprefix = "wg"'))
        config = warpgate_ssh.load_config(path)
        text = warpgate_ssh.render(config, warpgate_ssh.resolve(config))
        self.assertIn("Host wg-acme-prod1 wg-acmecorp-prod1\n", text)


class WriteAndAddTests(TempHome):
    def test_refuses_to_replace_a_hand_written_file_without_force(self) -> None:
        output = warpgate_ssh.default_output_path()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("Host mine\n")
        with self.assertRaisesRegex(ToolError, "--force"):
            warpgate_ssh.write_output(output, "# Generated by warpgate-ssh\n", assume_yes=True, force=False)
        self.assertEqual(output.read_text(), "Host mine\n")
        self.assertTrue(warpgate_ssh.write_output(output, "# Generated by warpgate-ssh\n", assume_yes=True, force=True))
        backups = list(warpgate_ssh.backup_root().glob("*/hosts.conf"))
        self.assertEqual([b.read_text() for b in backups], ["Host mine\n"])

    def test_parse_pasted_message(self) -> None:
        pasted = """Login with VPN on:

# Shop
ssh -p 2222 'me:shop-backend-01@gate.example.com'
ssh -p 2222 'me:shop-db-01@gate.example.com'
bare-target-name
ssh -p 2222 'me:shop-db-01@gate.example.com'
"""
        self.assertEqual(warpgate_ssh.parse_pasted(pasted), ["shop-backend-01", "shop-db-01", "bare-target-name"])

    def test_add_puts_each_target_in_its_project_list(self) -> None:
        path = warpgate_ssh.default_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(BASE + '\n[targets]\n# Acme\nacmecorp = [\n  "acme-corp-backend-01",\n]\n')
        added = warpgate_ssh.add_targets(path, ["acme-corp-backend-01", "acme-corp-db-01", "shop-redis", "bot-server"])
        self.assertEqual(added, ["acme-corp-db-01", "shop-redis", "bot-server"])
        text = path.read_text()
        self.assertIn('# Acme\nacmecorp = [\n  "acme-corp-backend-01",\n  "acme-corp-db-01",\n]', text)
        self.assertIn('\nshop = [\n  "shop-redis",\n]', text)
        self.assertIn('\nother = [\n  "bot-server",\n]', text)
        self.assertEqual(len(warpgate_ssh.load_config(path).targets), 4)

    def test_add_refuses_when_targets_is_not_the_last_table(self) -> None:
        path = warpgate_ssh.default_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        original = '[targets]\nacmecorp = [\n  "acme-corp-backend-01",\n]\n' + BASE
        path.write_text(original)
        with self.assertRaisesRegex(ToolError, "last section"):
            warpgate_ssh.add_targets(path, ["shop-redis"])
        self.assertEqual(path.read_text(), original)


if __name__ == "__main__":
    unittest.main()
