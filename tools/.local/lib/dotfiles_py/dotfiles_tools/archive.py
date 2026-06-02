"""Zstandard archive helpers."""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
from pathlib import Path

from . import notify, process
from .cli import ToolError, add_dry_run


def _human_size(bytes_value: int, base: int = 1000) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    value = float(bytes_value)
    for unit in units:
        if value < base or unit == units[-1]:
            return f"{value:.2f}{unit}" if unit != "B" else f"{int(value)}B"
        value /= base
    return f"{value:.2f}TB"


def _tree_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for root, _, files in os.walk(path):
        for file in files:
            try:
                total += (Path(root) / file).stat().st_size
            except OSError:
                pass
    return total


def _maybe_pause(enabled: bool) -> None:
    if enabled and sys.stdin.isatty():
        input("Press any key to close...")


def main_zstd_compress(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zstd-compress", description="Create a tar.zst archive.")
    parser.add_argument("target", nargs="?")
    parser.add_argument("output", nargs="?")
    parser.add_argument("--no-pause", action="store_true", help="do not wait before exiting")
    add_dry_run(parser)
    args = parser.parse_args(argv)
    if not args.target:
        raise ToolError("usage: zstd-compress <target_file_or_folder> [optional_output_name]")

    target = Path(args.target).expanduser()
    if not target.exists():
        raise ToolError(f"target not found: {target}")
    target = target.resolve()
    parent = target.parent
    item_name = target.name

    if args.output:
        output = Path(args.output).expanduser()
        if output.suffixes[-2:] != [".tar", ".zst"]:
            output = output.with_name(output.name + ".tar.zst")
        archive = output.resolve()
    else:
        archive = parent / f"{item_name}.tar.zst"
    if not archive.parent.is_dir():
        raise ToolError(f"output directory does not exist: {archive.parent}")

    total_size = _tree_size(target)
    zstd_level = "-4"
    strategy = "Max Speed/Efficiency"
    disk_type = "SSD (Flash/Fast)"
    device = process.output(["findmnt", "-n", "-o", "SOURCE", "--target", str(archive.parent)]).strip()
    if device:
        rota = process.output(["lsblk", "-d", "-n", "-o", "ROTA", device]).splitlines()
        if rota and rota[0].strip() == "1":
            zstd_level = "-8"
            strategy = "Max Density for HDD"
            disk_type = "HDD (Rotational)"

    print("===================================================")
    print("           SMART ZSTD ARCHIVER")
    print("===================================================")
    print(f" Input:      {item_name}")
    print(f" Output:     {archive.name}")
    print(f" Location:   {archive.parent}")
    print(f" Size:       {_human_size(total_size)}")
    print("---------------------------------------------------")
    print(f" Target Disk:{disk_type}")
    print(f" Strategy:   {strategy}")
    print(f" Settings:   Level {zstd_level} | Long Distance | Threads: All")
    print("===================================================")

    if args.dry_run:
        print(f"+ tar -cf - {item_name} | pv ... | zstd -T0 {zstd_level} --long > {archive}")
        return 0

    process.require("tar", "pv", "zstd")
    try:
        with archive.open("wb") as output:
            tar = subprocess.Popen(["tar", "-cf", "-", item_name], cwd=parent, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            pv = subprocess.Popen(
                ["pv", "-p", "-t", "-e", "-r", "-b", "--si", "-s", str(total_size)],
                stdin=tar.stdout,
                stdout=subprocess.PIPE,
            )
            if tar.stdout:
                tar.stdout.close()
            zstd = subprocess.Popen(["zstd", "-T0", zstd_level, "--long"], stdin=pv.stdout, stdout=output)
            if pv.stdout:
                pv.stdout.close()
            status = zstd.wait()
            tar.wait()
            pv.wait()
    except KeyboardInterrupt:
        if archive.exists():
            archive.unlink()
        notify.notify("Compression Cancelled", "Operation aborted by user.", icon="dialog-warning")
        os.kill(os.getpid(), signal.SIGINT)
        return 130

    if status == 0:
        archive_size = archive.stat().st_size
        saved = total_size - archive_size
        percent = ((total_size - archive_size) / total_size * 100) if total_size else 0
        print("SUCCESS! Archive created successfully.")
        print(f"Original Size:   {_human_size(total_size)}")
        print(f"Final Size:      {_human_size(archive_size)}")
        print(f"Space Saved:     {_human_size(saved)} ({percent:.2f}%)")
        notify.notify("Compression Success", f"Saved {_human_size(saved)} ({percent:.2f}%)\nArchive: {archive.name}", icon="package-x-generic")
    else:
        if archive.exists():
            archive.unlink()
        print(f"FAILED. Error code: {status}")
        notify.notify("Compression Failed", "Check terminal for error details", urgency="critical", icon="dialog-error")
    _maybe_pause(not args.no_pause)
    return status


def main_zstd_extract(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="zstd-extract", description="Extract a tar.zst archive.")
    parser.add_argument("archive", nargs="?")
    parser.add_argument("dest_dir", nargs="?")
    parser.add_argument("--no-pause", action="store_true", help="do not wait before exiting")
    add_dry_run(parser)
    args = parser.parse_args(argv)
    if not args.archive:
        raise ToolError("no archive provided")

    archive = Path(args.archive).expanduser()
    if not archive.is_file():
        raise ToolError(f"file not found: {archive}")
    archive = archive.resolve()
    base = archive.name
    for suffix in (".tar.zst", ".tar.gz", ".tar", ".zst"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    output = Path(args.dest_dir).expanduser() if args.dest_dir else archive.parent / base
    size = archive.stat().st_size
    print("===================================================")
    print("           ZSTD EXTRACTOR")
    print("===================================================")
    print(f" Archive:    {archive.name}")
    print(f" Extract To: {output}")
    print(f" Size:       {_human_size(size, 1024)}")
    print("---------------------------------------------------")

    if args.dry_run:
        print(f"+ mkdir -p {output}")
        print(f"+ pv ... {archive} | zstd -d | tar -x -C {output}")
        return 0

    process.require("pv", "zstd", "tar")
    output.mkdir(parents=True, exist_ok=True)
    pv = subprocess.Popen(["pv", "-p", "-t", "-e", "-r", "-b", "--si", "-s", str(size), str(archive)], stdout=subprocess.PIPE)
    zstd = subprocess.Popen(["zstd", "-d"], stdin=pv.stdout, stdout=subprocess.PIPE)
    if pv.stdout:
        pv.stdout.close()
    tar = subprocess.Popen(["tar", "-x", "-C", str(output)], stdin=zstd.stdout)
    if zstd.stdout:
        zstd.stdout.close()
    status = tar.wait()
    zstd.wait()
    pv.wait()

    if status == 0:
        print("SUCCESS! Extracted successfully.")
        notify.notify("Extraction Finished", f"Folder: {base}", icon="folder-open")
    else:
        print(f"FAILED. Error code: {status}")
        notify.notify("Extraction Failed", "Check terminal for details", urgency="critical", icon="dialog-error")
    _maybe_pause(not args.no_pause)
    return status

