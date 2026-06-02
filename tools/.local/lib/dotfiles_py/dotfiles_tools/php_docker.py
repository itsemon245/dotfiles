"""Docker-backed PHP and Composer wrappers."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from . import process
from .paths import home, xdg_cache_home, xdg_config_home


def _tool_help(name: str) -> str:
    if name == "composer":
        return "Usage: composer [COMPOSER_ARGS...]\nRuns Composer inside the configured PHP Docker image."
    if name == "sysphp":
        return "Usage: sysphp [PHP_ARGS...]\nRuns /usr/bin/php directly."
    return "Usage: php [PHP_ARGS...]\nRuns PHP inside the configured PHP Docker image."


def _base_args(tty_mode: str) -> tuple[list[str], str, str]:
    php_version = os.environ.get("PHP_VERSION", "8.4")
    image = os.environ.get("PHP_IMAGE", f"my/php:{php_version}-dev")
    network = os.environ.get("PHP_NETWORK", "host")
    cache_dir = xdg_cache_home() / "composer"
    config_dir = xdg_config_home()
    cache_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)

    args = [
        "docker",
        "run",
        "--rm",
        "-u",
        f"{os.getuid()}:{os.getgid()}",
        "--network",
        network,
        "-v",
        f"{Path.cwd()}:/app",
        "-w",
        "/app",
        "-v",
        f"{cache_dir}:/tmp/composer-cache",
        "-v",
        f"{config_dir}:/tmp/.config",
        "-e",
        "COMPOSER_CACHE_DIR=/tmp/composer-cache",
        "-e",
        "HOME=/tmp",
        "-e",
        "XDG_CONFIG_HOME=/tmp/.config",
    ]
    if sys.stdin.isatty() and sys.stdout.isatty():
        args.append("-it")
    elif tty_mode == "stdin":
        args.append("-i")
    return args, image, network


def _add_bridge_host(args: list[str], network: str) -> None:
    if network != "host":
        args.append("--add-host=host.docker.internal:host-gateway")


def _add_bridge_dns(args: list[str], network: str) -> None:
    if network != "host":
        args.extend(["--dns", "8.8.8.8", "--dns", "1.1.1.1"])


def _convert_project_args(argv: list[str]) -> list[str]:
    cwd = str(Path.cwd())
    converted = []
    for arg in argv:
        if arg.startswith("/") and arg.startswith(cwd + "/"):
            converted.append(arg[len(cwd) + 1 :])
        elif arg == cwd:
            converted.append(".")
        else:
            converted.append(arg)
    return converted


def _needs_ports(argv: list[str]) -> bool:
    if not argv:
        return False
    for arg in argv:
        if arg in {"--host", "--port", "-H", "-p"} or arg.startswith("--host=") or arg.startswith("--port="):
            return True
    first = argv[0]
    if first in {"serve", "octane", "roadrunner", "start", "server"}:
        return True
    if first == "artisan" and len(argv) > 1:
        second = argv[1]
        return second in {"serve", "start"} or second.startswith(("octane", "roadrunner", "reverb"))
    return False


def _port_spec(argv: list[str]) -> str:
    spec = os.environ.get("PHP_PORT_RANGE", "8000-8007")
    if argv and (argv[0] == "serve" or (argv[0] == "artisan" and len(argv) > 1 and argv[1] == "serve")):
        port = "8000"
        for index, arg in enumerate(argv):
            if arg.startswith("--port="):
                port = arg.split("=", 1)[1]
            elif arg in {"--port", "-p"} and index + 1 < len(argv):
                port = argv[index + 1]
        spec = f"{port}:{port}"
    if argv and argv[0] == "artisan" and len(argv) > 1 and argv[1].startswith("reverb"):
        server_port = os.environ.get("REVERB_SERVER_PORT", "8008")
        host_port = os.environ.get("REVERB_HOST_PORT", server_port)
        spec = f"{host_port}:{server_port}"
    return spec


def _add_ports(args: list[str], spec: str) -> None:
    args.extend(["-p", spec if ":" in spec else f"{spec}:{spec}"])


def _exec(command: list[str]) -> int:
    os.execvp(command[0], command)
    return 127


def main_php(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv == ["--dotfiles-tool-help"]:
        print(_tool_help("php"))
        return 0
    process.require("docker")
    args, image, network = _base_args("stdin")
    _add_bridge_dns(args, network)
    _add_bridge_host(args, network)
    if _needs_ports(argv) and network != "host":
        _add_ports(args, _port_spec(argv))
    return _exec([*args, image, "php", *_convert_project_args(argv)])


def main_composer(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv == ["--dotfiles-tool-help"]:
        print(_tool_help("composer"))
        return 0
    process.require("docker")
    args, image, network = _base_args("tty")
    _add_bridge_host(args, network)
    return _exec([*args, image, "composer", *argv])


def main_sysphp(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv == ["--dotfiles-tool-help"]:
        print(_tool_help("sysphp"))
        return 0
    executable = "/usr/bin/php"
    os.execv(executable, [executable, *argv])
    return 127

