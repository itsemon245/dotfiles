from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotfiles_tools import agecrypt, sshkey
from dotfiles_tools.cli import ToolError


class TempHome(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="agecrypt-test-"))
        env = {"HOME": str(self.tmp), "XDG_CONFIG_HOME": str(self.tmp / ".config")}
        for name in ("AGECRYPT_IDENTITY", "AGECRYPT_RECIPIENTS", "SSHKEY_DIR", "SSHKEY_ENCRYPTED_DIR"):
            env[name] = ""
        self.env = patch.dict(os.environ, env)
        self.env.start()
        for name in ("AGECRYPT_IDENTITY", "AGECRYPT_RECIPIENTS", "SSHKEY_DIR", "SSHKEY_ENCRYPTED_DIR"):
            del os.environ[name]

    def tearDown(self) -> None:
        self.env.stop()
        assert self.tmp.name.startswith("agecrypt-test-") and self.tmp.parent == Path(tempfile.gettempdir())
        shutil.rmtree(self.tmp)


class NamingTest(TempHome):
    def test_encrypted_and_decrypted_names(self) -> None:
        key = self.tmp / "keys" / "homelab"
        self.assertEqual(agecrypt.encrypted_name(key, None), self.tmp / "keys" / "homelab.age")
        self.assertEqual(agecrypt.encrypted_name(key, self.tmp / "enc"), self.tmp / "enc" / "homelab.age")
        self.assertEqual(agecrypt.decrypted_name(self.tmp / "enc" / "homelab.pub.age", self.tmp / "k"), self.tmp / "k" / "homelab.pub")
        with self.assertRaises(ToolError):
            agecrypt.decrypted_name(self.tmp / "homelab", None)

    def test_quoted_globs_expand_in_order_without_duplicates(self) -> None:
        for name in ("b", "a", "a.pub"):
            (self.tmp / name).write_text(name)
        found = agecrypt.expand_inputs([str(self.tmp / "a*"), str(self.tmp / "a"), str(self.tmp / "b")])
        self.assertEqual(found, [self.tmp / "a", self.tmp / "a.pub", self.tmp / "b"])
        with self.assertRaises(ToolError):
            agecrypt.expand_inputs([str(self.tmp / "missing*")])

    def test_recipients_file_is_found_by_walking_up(self) -> None:
        nested = self.tmp / "repo" / ".ssh" / "encrypted"
        nested.mkdir(parents=True)
        recipients = self.tmp / "repo" / agecrypt.RECIPIENTS_FILENAME
        recipients.write_text("age1example\n")
        self.assertEqual(agecrypt.find_recipients_file(nested), recipients)
        self.assertEqual(agecrypt.recipient_args([], None, nested), ["-R", str(recipients)])

    def test_explicit_recipient_wins(self) -> None:
        self.assertEqual(agecrypt.recipient_args(["age1abc"], None, self.tmp), ["-r", "age1abc"])

    def test_missing_recipient_is_an_error(self) -> None:
        with self.assertRaises(ToolError):
            agecrypt.recipient_args([], None, self.tmp)


class SshKeyTest(TempHome):
    def test_names_go_to_the_keys_dir_and_paths_are_kept(self) -> None:
        self.assertEqual(sshkey.key_path("homelab", None), self.tmp / ".ssh" / "keys" / "homelab")
        self.assertEqual(sshkey.key_path("~/elsewhere/k", None), self.tmp / "elsewhere" / "k")
        self.assertEqual(sshkey.key_path("k", self.tmp / "d"), self.tmp / "d" / "k")

    def test_only_default_dir_keys_are_encrypted_by_default(self) -> None:
        (self.tmp / ".ssh" / "keys").mkdir(parents=True)
        self.assertTrue(sshkey.in_default_dir(sshkey.key_path("homelab", None)))
        self.assertFalse(sshkey.in_default_dir(self.tmp / "elsewhere" / "k"))

    def test_keygen_command(self) -> None:
        command = sshkey.keygen_command(Path("/k"), key_type="ed25519", comment="c", no_passphrase=True)
        self.assertEqual(command, ["ssh-keygen", "-t", "ed25519", "-a", "100", "-C", "c", "-f", "/k", "-N", ""])


@unittest.skipUnless(shutil.which("age") and shutil.which("age-keygen") and shutil.which("ssh-keygen"), "age not installed")
class RoundTripTest(TempHome):
    def test_sshkey_encrypts_and_agecrypt_restores_identical_files(self) -> None:
        identity = agecrypt.default_identity_path()
        recipient = agecrypt.keygen(identity)
        self.assertTrue(recipient.startswith("age1"))
        self.assertEqual(identity.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(ToolError):
            agecrypt.keygen(identity)  # never replaced

        with patch("builtins.print"):
            sshkey.main(["demo", "-N"])
        keys = self.tmp / ".ssh" / "keys"
        encrypted = self.tmp / ".ssh" / "encrypted"
        self.assertEqual(sorted(p.name for p in encrypted.iterdir()), ["demo.age", "demo.pub.age"])
        self.assertNotIn(b"PRIVATE KEY", (encrypted / "demo.age").read_bytes())

        restored = self.tmp / "restored"
        agecrypt.decrypt(sorted(encrypted.iterdir()), out_dir=restored)
        self.assertEqual((restored / "demo").read_bytes(), (keys / "demo").read_bytes())
        self.assertEqual((restored / "demo").stat().st_mode & 0o777, 0o600)
        with self.assertRaises(ToolError):
            agecrypt.decrypt([encrypted / "demo.age"], out_dir=restored)  # refuses to overwrite

    def test_pasted_identity_is_used_when_no_identity_file_exists(self) -> None:
        identity = self.tmp / "vault-copy.txt"
        agecrypt.keygen(identity)
        secret = next(line for line in identity.read_text().splitlines() if line.startswith(agecrypt.SECRET_PREFIX))
        (self.tmp / "note").write_text("hello")
        agecrypt.encrypt([self.tmp / "note"], recipients=[agecrypt.public_recipient(identity)])
        (self.tmp / "note").unlink()
        with patch.object(agecrypt, "_pasted_identity", return_value=(secret + "\n").encode()):
            agecrypt.decrypt([self.tmp / "note.age"])
        self.assertEqual((self.tmp / "note").read_text(), "hello")


if __name__ == "__main__":
    unittest.main()
