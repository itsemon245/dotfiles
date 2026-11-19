"""Encrypt and decrypt files with age, using one identity kept in a password manager.

Encryption only needs the *public* recipient, so it never asks for a secret. The
recipient comes from, in order: -r/--recipient, -R/--recipients-file,
$AGECRYPT_RECIPIENTS, the nearest `.age-recipients` file above the output, or the
public half of the default identity.

Decryption needs the *private* identity: -i/--identity, $AGECRYPT_IDENTITY,
~/.config/age/identity.txt, or a hidden prompt where you paste it from the
password manager. A pasted identity is piped to age on stdin and never written to disk.

Outputs are never overwritten unless --force is given, and decrypted files are 0600.
"""

from __future__ import annotations

import argparse
import getpass
import glob
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from .cli import ToolError
from .paths import expand, xdg_config_home
from .process import require

SUFFIX = ".age"
RECIPIENTS_FILENAME = ".age-recipients"
SECRET_PREFIX = "AGE-SECRET-KEY-"


def default_identity_path() -> Path:
    override = os.environ.get("AGECRYPT_IDENTITY")
    return expand(override) if override else xdg_config_home() / "age" / "identity.txt"


def expand_inputs(patterns: list[str]) -> list[Path]:
    """Expand globs that the shell left alone (quoted patterns) and keep order, without duplicates."""
    paths: list[Path] = []
    for pattern in patterns:
        matches = sorted(glob.glob(os.path.expanduser(pattern))) if glob.has_magic(pattern) else [os.path.expanduser(pattern)]
        if not matches:
            raise ToolError(f"no files match {pattern}")
        for match in matches:
            path = Path(match)
            if path not in paths:
                paths.append(path)
    return paths


def encrypted_name(path: Path, out_dir: Path | None) -> Path:
    return (out_dir or path.parent) / (path.name + SUFFIX)


def decrypted_name(path: Path, out_dir: Path | None) -> Path:
    if path.suffix != SUFFIX:
        raise ToolError(f"{path} does not end in {SUFFIX}")
    return (out_dir or path.parent) / path.stem


def find_recipients_file(start: Path) -> Path | None:
    """Walk up from `start` looking for a `.age-recipients` file, like git does for .gitignore."""
    current = start.resolve()
    for directory in (current, *current.parents):
        candidate = directory / RECIPIENTS_FILENAME
        if candidate.is_file():
            return candidate
    return None


def public_recipient(identity: Path) -> str:
    require("age-keygen")
    completed = subprocess.run(["age-keygen", "-y", str(identity)], capture_output=True, text=True)
    if completed.returncode != 0:
        raise ToolError(f"could not read the public key of {identity}: {completed.stderr.strip()}")
    return completed.stdout.strip()


def recipient_args(recipients: list[str], recipients_file: Path | None, out_dir: Path) -> list[str]:
    if recipients:
        return [arg for recipient in recipients for arg in ("-r", recipient)]
    candidates = [recipients_file]
    env_file = os.environ.get("AGECRYPT_RECIPIENTS")
    candidates.append(expand(env_file) if env_file else None)
    candidates.append(find_recipients_file(out_dir))
    for candidate in candidates:
        if candidate is not None:
            if not candidate.is_file():
                raise ToolError(f"recipients file not found: {candidate}")
            return ["-R", str(candidate)]
    identity = default_identity_path()
    if identity.is_file():
        return ["-r", public_recipient(identity)]
    raise ToolError(
        f"no recipient: pass -r, set AGECRYPT_RECIPIENTS, add a {RECIPIENTS_FILENAME} file, "
        f"or create an identity with `agecrypt keygen`"
    )


def _check_output(target: Path, force: bool) -> None:
    if target.exists() and not force:
        raise ToolError(f"{target} already exists (use --force to replace it)")


def _run_age_to(target: Path, flags: list[str], source: Path, *, stdin: bytes | None, mode: int) -> None:
    """Run age writing to a temp file beside `target`, then move it into place.

    age wants every flag (including -o) before the input file.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        os.chmod(tmp, mode)
        completed = subprocess.run(["age", *flags, "-o", str(tmp), str(source)], input=stdin, capture_output=True)
        if completed.returncode != 0:
            raise ToolError(f"age failed for {target}: {completed.stderr.decode(errors='replace').strip()}")
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)


def encrypt(
    inputs: list[Path],
    *,
    out_dir: Path | None = None,
    recipients: list[str] | None = None,
    recipients_file: Path | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> list[Path]:
    require("age")
    plan = [(path, encrypted_name(path, out_dir)) for path in inputs]
    for source, target in plan:
        if not source.is_file():
            raise ToolError(f"not a file: {source}")
        _check_output(target, force)
    written = []
    for source, target in plan:
        args = ["-e", *recipient_args(recipients or [], recipients_file, target.parent)]
        if dry_run:
            print(f"+ encrypt {source} -> {target}")
            continue
        _run_age_to(target, args, source, stdin=None, mode=0o644)
        written.append(target)
    return written


def _pasted_identity() -> bytes:
    if not sys.stdin.isatty():
        raise ToolError("no identity file found and stdin is not a terminal to paste one")
    secret = getpass.getpass("Paste the age identity (AGE-SECRET-KEY-…): ").strip()
    if not secret.startswith(SECRET_PREFIX):
        raise ToolError("that does not look like an age identity")
    return (secret + "\n").encode()


def decrypt(
    inputs: list[Path],
    *,
    out_dir: Path | None = None,
    identity: Path | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> list[Path]:
    require("age")
    plan = [(path, decrypted_name(path, out_dir)) for path in inputs]
    for source, target in plan:
        if not source.is_file():
            raise ToolError(f"not a file: {source}")
        _check_output(target, force)
    if dry_run:
        for source, target in plan:
            print(f"+ decrypt {source} -> {target}")
        return []

    identity_path = identity or default_identity_path()
    pasted = None
    if identity is not None and not identity.is_file():
        raise ToolError(f"identity file not found: {identity}")
    if not identity_path.is_file():
        pasted = _pasted_identity()  # asked once, reused for every file
    written = []
    for source, target in plan:
        identity_arg = "-" if pasted is not None else str(identity_path)
        _run_age_to(target, ["-d", "-i", identity_arg], source, stdin=pasted, mode=0o600)
        written.append(target)
    return written


def keygen(path: Path) -> str:
    """Create an identity at `path` (0600) and return its public recipient. The secret is never printed.

    There is deliberately no --force: replacing an identity makes every file encrypted to it unreadable.
    """
    require("age-keygen")
    if path.exists():
        raise ToolError(f"{path} already exists; move it away yourself if you really mean to replace it")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    completed = subprocess.run(["age-keygen", "-o", str(path)], capture_output=True, text=True)
    if completed.returncode != 0:
        raise ToolError(f"age-keygen failed: {completed.stderr.strip()}")
    os.chmod(path, 0o600)
    return public_recipient(path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agecrypt",
        description="Encrypt and decrypt files with age. Encrypting needs only the public recipient.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    enc = sub.add_parser("encrypt", aliases=["e"], help="encrypt files to FILE.age")
    enc.add_argument("files", nargs="+", help="files or quoted globs")
    enc.add_argument("-o", "--out-dir", type=expand, help="write FILE.age here instead of beside FILE")
    enc.add_argument("-r", "--recipient", action="append", default=[], help="age public key (repeatable)")
    enc.add_argument("-R", "--recipients-file", type=expand, help="file of age public keys")

    dec = sub.add_parser("decrypt", aliases=["d"], help="decrypt FILE.age to FILE")
    dec.add_argument("files", nargs="+", help=".age files or quoted globs")
    dec.add_argument("-o", "--out-dir", type=expand, help="write FILE here instead of beside FILE.age")
    dec.add_argument("-i", "--identity", type=expand, help="identity file (default: ~/.config/age/identity.txt, else prompt)")

    for command in (enc, dec):
        command.add_argument("-f", "--force", action="store_true", help="replace existing outputs")
        command.add_argument("--dry-run", action="store_true", help="show what would be written")

    gen = sub.add_parser("keygen", help="create an identity and print its public recipient")
    gen.add_argument("-o", "--output", type=expand, help="identity path (default: ~/.config/age/identity.txt)")

    pub = sub.add_parser("recipient", help="print the public recipient of an identity")
    pub.add_argument("-i", "--identity", type=expand, help="identity file (default: ~/.config/age/identity.txt)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command in ("encrypt", "e"):
        for path in encrypt(expand_inputs(args.files), out_dir=args.out_dir, recipients=args.recipient,
                            recipients_file=args.recipients_file, force=args.force, dry_run=args.dry_run):
            print(path)
    elif args.command in ("decrypt", "d"):
        for path in decrypt(expand_inputs(args.files), out_dir=args.out_dir, identity=args.identity,
                            force=args.force, dry_run=args.dry_run):
            print(path)
    elif args.command == "keygen":
        path = args.output or default_identity_path()
        recipient = keygen(path)
        print(f"Identity written to {path} (mode 0600). Store its contents in your password manager.")
        print(recipient)
    elif args.command == "recipient":
        print(public_recipient(args.identity or default_identity_path()))
    return 0
