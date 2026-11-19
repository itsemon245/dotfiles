"""Generate SSH key pairs with sane defaults.

`sshkey homelab` writes ~/.ssh/keys/homelab and homelab.pub (ed25519, 100 KDF rounds)
and prints the public key. A NAME containing a slash is used as a path instead.

When the key lands under a folder with a `.age-recipients` file above it (such as the
secrets repo behind ~/.ssh), the private key is also encrypted with agecrypt to
NAME.age beside it. Public keys are not secret and are left as they are. Encryption
uses the public age recipient, so it does not ask for a secret.
"""

from __future__ import annotations

import argparse
import getpass
import os
import socket
import subprocess
from pathlib import Path

from . import agecrypt
from .cli import ToolError
from .paths import expand, home
from .process import require

TYPES = {"ed25519": ["-t", "ed25519", "-a", "100"], "rsa": ["-t", "rsa", "-b", "4096", "-a", "100"]}


def keys_dir() -> Path:
    override = os.environ.get("SSHKEY_DIR")
    return expand(override) if override else home() / ".ssh" / "keys"


def key_path(name: str, directory: Path | None) -> Path:
    if "/" in name or name.startswith("~"):
        return expand(name)
    return (directory or keys_dir()) / name


def default_comment(name: str) -> str:
    return f"{Path(name).name} {getpass.getuser()}@{socket.gethostname()}"


def encrypts_by_default(path: Path) -> bool:
    """Encrypt keys that live in a tree managed by agecrypt (one with a .age-recipients file)."""
    return agecrypt.find_recipients_file(path.parent) is not None


def keygen_command(path: Path, *, key_type: str, comment: str, no_passphrase: bool) -> list[str]:
    command = ["ssh-keygen", *TYPES[key_type], "-C", comment, "-f", str(path)]
    if no_passphrase:
        command.extend(["-N", ""])
    return command


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sshkey", description="Generate an SSH key pair with sane defaults.")
    parser.add_argument("name", help="key name (saved in ~/.ssh/keys) or a path containing a slash")
    parser.add_argument("-t", "--type", choices=sorted(TYPES), default="ed25519", help="key type (default: ed25519)")
    parser.add_argument("-C", "--comment", help="key comment (default: '<name> <user>@<host>')")
    parser.add_argument("-d", "--dir", type=expand, help="directory for NAME (default: ~/.ssh/keys)")
    parser.add_argument("-N", "--no-passphrase", action="store_true", help="create the key without a passphrase")
    encrypt = parser.add_mutually_exclusive_group()
    encrypt.add_argument("--encrypt", dest="encrypt", action="store_true", default=None,
                         help="encrypt the private key to NAME.age (default when a .age-recipients file is above it)")
    encrypt.add_argument("--no-encrypt", dest="encrypt", action="store_false", help="never encrypt the private key")
    parser.add_argument("--dry-run", action="store_true", help="show what would run")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    path = key_path(args.name, args.dir)
    public = path.with_name(path.name + ".pub")
    encrypted = agecrypt.encrypted_name(path, None)
    for existing in (path, public, encrypted):
        if existing.exists():
            raise ToolError(f"{existing} already exists; pick another name")

    command = keygen_command(
        path,
        key_type=args.type,
        comment=args.comment or default_comment(args.name),
        no_passphrase=args.no_passphrase,
    )
    should_encrypt = encrypts_by_default(path) if args.encrypt is None else args.encrypt

    if args.dry_run:
        print("+ " + " ".join(command))
        if should_encrypt:
            print(f"+ encrypt {path} -> {encrypted}")
        return 0

    require("ssh-keygen")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if subprocess.run(command).returncode != 0:
        raise ToolError("ssh-keygen failed")

    if should_encrypt:
        for written in agecrypt.encrypt([path]):
            print(f"Encrypted copy: {written}")
    print(public.read_text().strip())
    return 0
