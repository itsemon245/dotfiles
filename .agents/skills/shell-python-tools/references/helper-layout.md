# Tool And Helper Layout Reference

## Canonical Structure

```text
tools/
  .local/bin/
    wally
    rofi-vpn
    ...

  .local/lib/dotfiles/
    shell/
      path.sh
      source.sh
      env.sh
      common.sh

  .local/lib/dotfiles_py/
    dotfiles_tools/
      __init__.py
      cli.py
      process.py
      notify.py
      paths.py
      rofi.py
      wallpaper.py
      vpn.py
      hypr.py
      php_docker.py
```

## Meaning

- `tools/.local/bin`: user-facing commands and tiny Python launchers.
- `tools/.local/lib/dotfiles/shell`: startup-safe shell helpers for `.zshrc`, `.bashrc`, `exports.sh`, and sourced files.
- `tools/.local/lib/dotfiles/tool`: removed transitional Bash executable-helper layer. Do not reintroduce it for maintained tools.
- `tools/.local/lib/dotfiles_py/dotfiles_tools`: Python helper package for maintained executable tools.

## Startup-Safe Shell Helpers

Use `shell/` for functions that are safe to source in an interactive shell:

- `path.sh`: `path_prepend`, `path_append`, `path_remove`, `path_contains`
- `source.sh`: `source_if_exists`, `source_dir_if_exists`
- `env.sh`: `command_exists`, `is_interactive`, `has_display`
- `common.sh`: startup-safe aggregate import

Startup-safe helper files must not print, exit, start background services, run desktop commands, or require optional dependencies at source time.

## Python Tool Helpers

Use `dotfiles_tools/` for maintained executable tools:

- `cli.py`: argparse helpers, common result/exit handling
- `process.py`: command detection, subprocess wrappers, dry-run support
- `notify.py`: notification adapter using `dunstify`, `notify-send`, or `hyprctl`
- `paths.py`: XDG/cache/config/path helpers
- `rofi.py`: Rofi menu input/output helpers
- `wallpaper.py`: wallpaper/theme orchestration helpers
- `vpn.py`: NetworkManager/WireGuard helpers
- `hypr.py`: Hyprland startup/window helpers
- `php_docker.py`: PHP/Composer Docker wrapper helpers

Python modules should be stdlib-first, importable without desktop commands installed, and free of import-time side effects.

## Entrypoints

Prefer one of these patterns for `tools/.local/bin/<command>`:

1. A direct Python script with the real command logic kept small and readable.
2. A tiny Python launcher that resolves `../lib/dotfiles_py`, adds it to `sys.path`, and calls `dotfiles_tools.<tool>.main()`.
3. A tiny Bash wrapper only when shell-native setup is the whole job and no known call site can be updated directly.

Do not put large fallback helper definitions in command entrypoints. If a command needs reusable behavior, move the command body into Python modules.

## Bash Tool Helpers

The Phase 2 Bash executable-tool helper layer has been removed. Keep a Bash tool only when the shell version is obviously shorter and clearer than Python, and keep any such script standalone.

Do not add `tools/.local/lib/dotfiles/tool` again unless there is a new, deliberate shell-native tool family with multiple real callers.

## Promotion Rule

Do not start by inventing a large taxonomy.

- One caller: keep logic local.
- One complex Python tool: private function/class in that tool module.
- Two or more real callers: candidate for an existing behavior module.
- Coherent group: move to a named Python module.
- Large module: split by behavior before adding more unrelated helpers.

## Validation

- Shell startup helpers: `bash -n`, `zsh -n`, and source from Bash/zsh.
- Python helpers: `python -m compileall tools/.local/lib/dotfiles_py`.
- Python tools: `--help` smoke checks, focused unit tests where useful, temp HOME checks, and stowed/copy-tree launcher checks.
- Desktop/system actions: validate through dry-run, mocks, or harmless command paths instead of changing live wallpaper, VPN, services, containers, or user data.

## Naming

Prefer boring names that describe behavior. Avoid clever project-specific abbreviations in helper names. Prefix only when needed to avoid collision or make call sites clearer.
