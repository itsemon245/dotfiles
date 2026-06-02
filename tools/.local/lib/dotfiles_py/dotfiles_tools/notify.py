"""Desktop notification adapter."""

from __future__ import annotations

from . import process


def notify(
    title: str,
    message: str = "",
    *,
    urgency: str = "normal",
    icon: str | None = None,
    timeout: int = 5000,
    replace_id: int | None = None,
    dry_run: bool = False,
) -> None:
    if process.command_exists("dunstify"):
        args = ["dunstify", title, message, "-u", urgency, "-t", str(timeout)]
        if replace_id is not None:
            args.extend(["-r", str(replace_id)])
        if icon:
            args.extend(["-i", icon])
        process.run(args, dry_run=dry_run, quiet=True)
        return

    if process.command_exists("notify-send"):
        args = ["notify-send", title, message, "-u", urgency, "-t", str(timeout)]
        if icon:
            args.extend(["-i", icon])
        process.run(args, dry_run=dry_run, quiet=True)
        return

    if process.command_exists("hyprctl"):
        process.run(
            ["hyprctl", "notify", "-1", str(timeout), "rgb(ffb86c)", f"{title}: {message}"],
            dry_run=dry_run,
            quiet=True,
        )
        return

    if urgency == "critical":
        print(f"{title}: {message}")


def progress(
    title: str,
    message: str,
    percent: int,
    *,
    urgency: str = "normal",
    icon: str | None = None,
    timeout: int = 0,
    replace_id: int | None = None,
    dry_run: bool = False,
) -> None:
    if process.command_exists("dunstify"):
        args = [
            "dunstify",
            title,
            message,
            "-u",
            urgency,
            "-t",
            str(timeout),
            "-h",
            f"int:value:{percent}",
        ]
        if replace_id is not None:
            args.extend(["-r", str(replace_id)])
        if icon:
            args.extend(["-i", icon])
        process.run(args, dry_run=dry_run, quiet=True)
        return

    notify(
        title,
        message,
        urgency=urgency,
        icon=icon,
        timeout=timeout,
        replace_id=replace_id,
        dry_run=dry_run,
    )
