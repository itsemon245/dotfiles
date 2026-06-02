# Shell/Python Tool Boundary Rule

## Default Boundary

Use shell for interactive shell startup and genuinely shell-native glue.

Use Python for maintained executable tools once they need shared logic, structured parsing, subprocess orchestration, desktop adapters, cache/temp handling, or tests.

Do not keep compatibility wrappers in old package-local command locations when all known call sites can be updated to the canonical `tools/.local/bin` command.

## Shell Stays For

- `.zshrc`, `.bashrc`, `exports.sh`, aliases, and files sourced by an interactive shell.
- Simple installer/bootstrap glue where Bash is clearer because the work is shell-native.
- Very small one-off scripts that are shorter and clearer than a Python equivalent.

Shell startup must not depend on Python, uv, Lua, desktop commands, package managers, or network access.

## Python Becomes Default For

- Maintained commands under `tools/.local/bin`.
- Desktop orchestration tools such as `wally`, Rofi tools, Hyprland startup orchestration, wallpaper/theme reloaders, and NetworkManager/VPN tools.
- Portable tools that need argument parsing, validation, subprocess pipelines, formatting, or testable helpers.
- Wrappers such as PHP/Composer Docker commands once the setup logic is shared or conditional.

Prefer stdlib-only Python first. Use `uv` for development/test commands and for tools that genuinely require third-party dependencies. Do not make a command resolve or download dependencies at runtime unless the user explicitly asked the command to do network/dependency work.

## Lua Boundary

Use Lua only where Lua is native to the target application or clearly simpler than Python for that specific tool. Neovim configuration belongs in Lua; desktop orchestration generally belongs in Python.

## Canonical Tool Layout

Keep the tool package layout boring and stow-friendly:

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

- `tools/.local/bin`: canonical user-facing commands.
- `tools/.local/lib/dotfiles/shell`: startup-safe shell helpers.
- `tools/.local/lib/dotfiles_py/dotfiles_tools`: importable Python modules for maintained executable tools.

Entrypoints should either be direct Python scripts or tiny launchers that add `../lib/dotfiles_py` to `sys.path` and call `dotfiles_tools.<tool>.main()`.

## Helper Design

- Startup-safe shell helpers live under `tools/.local/lib/dotfiles/shell`.
- Python tool helpers live under `tools/.local/lib/dotfiles_py/dotfiles_tools`.
- The previous Bash executable-tool helper layer under `tools/.local/lib/dotfiles/tool` has been removed. Do not reintroduce it for maintained tools; move reusable tool logic into Python modules instead.
- Helper files/modules must not print, exit the parent shell, mutate unrelated state, or probe desktop/runtime dependencies at import/source time.
- Add a helper only after behavior is repeated across maintained files or meaningfully clarifies a complex file.
- Group helpers by behavior, not by abstract taxonomy.

## Migration Criteria

Move a Bash executable tool to Python when any of these are true:

- The script needs more than a tiny wrapper/import block.
- Reusable Bash helper loading makes the tool harder to read.
- The tool needs structured arguments, JSON/TOML/text parsing, cache paths, retries, process orchestration, or testable units.
- Similar behavior is duplicated across two or more maintained tools.

Keep a tool in shell when the shell version is obviously shorter, clearer, and unlikely to need shared logic.

## Validation

For shell startup and wrappers:

- `bash -n` for Bash files.
- `zsh -n` for zsh startup files.
- Source startup helpers in Bash and zsh.
- Test symlinked startup directories such as `~/aliases`.

For Python tools:

- `python -m compileall` for the Python library.
- Focused unit tests for shared helpers when useful.
- `--help` or harmless smoke tests for each migrated command.
- Temp HOME and stowed/copy-tree launcher checks.
- Mock or dry-run system actions instead of changing wallpaper, VPN, services, containers, or user data during validation.
