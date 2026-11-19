"""Generate SSH key pairs with sane defaults.

`sshkey homelab` writes ~/.ssh/keys/homelab and homelab.pub (ed25519, 100 KDF rounds)
and prints the public key. A NAME containing a slash is used as a path instead.

Keys created in the default keys directory are also encrypted with agecrypt into
~/.ssh/encrypted/ (the committed directory), unless --no-encrypt is given. Encryption
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


def encrypted_dir() -> Path:
    override = os.environ.get("SSHKEY_ENCRYPTED_DIR")
    return expand(override) if override else home() / ".ssh" / "encrypted"


def key_path(name: str, directory: Path | None) -> Path:
    if "/" in name or name.startswith("~"):
        return expand(name)
    return (directory or keys_dir()) / name


def default_comment(name: str) -> str:
    return f"{Path(name).name} {getpass.getuser()}@{socket.gethostname()}"


def in_default_dir(path: Path) -> bool:
    return path.parent.resolve() == keys_dir().resolve()


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
                         help="also encrypt the pair with agecrypt (default only for ~/.ssh/keys)")
    encrypt.add_argument("--no-encrypt", dest="encrypt", action="store_false", help="never encrypt the pair")
    parser.add_argument("--encrypted-dir", type=expand, help="where encrypted copies go (default: ~/.ssh/encrypted)")
    parser.add_argument("--dry-run", action="store_true", help="show what would run")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    path = key_path(args.name, args.dir)
    public = path.with_name(path.name + ".pub")
    for existing in (path, public):
        if existing.exists():
            raise ToolError(f"{existing} already exists; pick another name")

    command = keygen_command(
        path,
        key_type=args.type,
        comment=args.comment or default_comment(args.name),
        no_passphrase=args.no_passphrase,
    )
    should_encrypt = in_default_dir(path) if args.encrypt is None else args.encrypt
    out_dir = args.encrypted_dir or encrypted_dir()

    if args.dry_run:
        print("+ " + " ".join(command))
        if should_encrypt:
            print(f"+ encrypt {path} and {public} -> {out_dir}/")
        return 0

    require("ssh-keygen")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if subprocess.run(command).returncode != 0:
        raise ToolError("ssh-keygen failed")

    if should_encrypt:
        for written in agecrypt.encrypt([path, public], out_dir=out_dir):
            print(f"Encrypted copy: {written}")
    print(public.read_text().strip())
    return 0
