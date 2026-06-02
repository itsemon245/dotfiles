---
name: shell-python-tools
description: Use when adding, updating, reviewing, or refactoring Bash/Zsh shell startup files, sourced shell libraries, dotfiles helper utilities, Python dotfiles tools, tiny executable wrappers, or maintained commands in this dotfiles repo. Applies to `.zshrc`, `.bashrc`, `exports.sh`, aliases, setup scripts, `tools/.local/lib/dotfiles`, `tools/.local/lib/dotfiles_py`, `*/bin/*` scripts, and helper promotion into named shell or Python modules.
---

# Shell/Python Dotfiles Tools

Use this skill for shell startup work and maintained dotfiles tools in this repo.

## Required Context

Before editing shell helpers or scripts, read:

- `.agents/rules/shell-python-tools.md` for the current shell/Python boundary rule
- `.agents/skills/shell-python-tools/references/helper-layout.md` when touching helper structure, imports, launchers, or `common.sh`

## Workflow

1. Classify the touched file by behavior, not by directory alone:
   - `sourced-startup`: `.zshrc`, `.bashrc`, `exports.sh`
   - `sourced-library`: aliases, helper files, files that are sourced
   - `python-tool`: maintained commands like `wally`, `rofi-vpn`, `rofi-cast`, desktop startup orchestration, and reusable tool modules
   - `tiny-shell-wrapper`: shell-native launchers that cannot be replaced by updating call sites
   - `shell-tool`: very small standalone scripts that are clearly shorter and clearer in shell
   - `installer-helper`: install/bootstrap/package scripts
2. Preserve the shell/Python boundary. Shell startup stays shell; maintained executable tools should move to Python when they need reusable logic, structured parsing, subprocess orchestration, or tests.
3. Prefer this extraction ladder for startup shell files:
   - keep single-use logic local;
   - extract a private function inside the same file;
   - move repeated helper logic to `common.sh` as an incubator;
   - move coherent helper groups from `common.sh` to a named module.
4. Prefer this extraction ladder for Python tools:
   - keep one-off logic inside the tool module;
   - extract private functions/classes inside that module;
   - promote repeated behavior into `dotfiles_tools/<behavior>.py`;
   - keep launchers tiny and move real logic into importable modules.
5. Keep sourced shell files quiet and safe. They must not print during normal startup, exit the parent shell, start agents, run desktop commands, or require optional tools while being sourced.
6. Keep executable tools explicit. Dependency checks should happen at command execution time, not at import/source time.
7. Validate narrowly after edits.

## Sourced Startup Rules

For `.zshrc`, `.bashrc`, `exports.sh`, aliases, and sourced helpers:

- Avoid `exit`; use `return` only when safe for sourced context.
- Avoid `set -euo pipefail` in files that are sourced by an interactive shell.
- Avoid `local` at file scope.
- Guard optional files with `source_if_exists` or explicit `[[ -f ... ]]` checks.
- Use path helpers for PATH mutation instead of repeated `export PATH=...` lines.
- Do not print unless the user requested debug output or an interactive command explicitly runs.

## Python Tool Rules

For maintained executable tools:

- Prefer Python over Bash when the tool has shared logic, real argument parsing, subprocess orchestration, desktop adapters, cache/temp handling, or tests.
- Prefer stdlib-only Python. Use `uv` for development/test workflows and only for runtime dependencies when a third-party package is genuinely needed.
- Put reusable code under `tools/.local/lib/dotfiles_py/dotfiles_tools`.
- Keep `tools/.local/bin/<command>` as a direct Python script or a tiny launcher that adds `../lib/dotfiles_py` to `sys.path` and calls a module `main()`.
- Prefer updating known call sites to the canonical `tools/.local/bin` command over keeping compatibility wrappers in old package-local locations.
- Use `argparse`, `pathlib`, `subprocess.run`, explicit return codes, and small behavior-oriented modules.
- Check external commands such as `rofi`, `hyprctl`, `wallust`, `nmcli`, `docker`, `notify-send`, and `dunstify` at the call site that needs them.
- Do not require network access at command startup unless the command itself is performing requested network work.
- Preserve command names and existing CLI behavior unless a deliberate breaking change is documented.

## Shell Tool Rules

For tiny wrappers and intentionally shell-native tools:

- Use `#!/usr/bin/env bash` unless there is a documented reason not to.
- Prefer `set -Eeuo pipefail` for standalone scripts after confirming current behavior can support it.
- Keep wrappers tiny. If a wrapper grows imports, fallbacks, and repeated helper definitions, migrate the tool body to Python.
- Do not reintroduce `tools/.local/lib/dotfiles/tool`; that transitional Bash executable-helper layer was removed after the Python migration.
- Keep desktop adapters optional: missing `rofi`, `notify-send`, `dunstify`, `hyprctl`, or `wallust` should fail only for modes that require them.

## Helper Promotion

When moving helpers from `common.sh` to a named module:

1. Identify the first real callers.
2. Choose the nearest startup-safe behavior name, such as `path.sh`, `source.sh`, or `env.sh`.
3. Move only the coherent group, not unrelated helpers.
4. Update all source/import lines.
5. Keep the old `common.sh` free of dead aliases unless compatibility is needed and documented.
6. Run syntax checks for every touched sourced file and executable script.

When promoting Python helpers:

1. Identify the first real callers.
2. Choose a behavior name such as `cli.py`, `process.py`, `notify.py`, `paths.py`, `rofi.py`, `wallpaper.py`, `vpn.py`, `hypr.py`, or `php_docker.py`.
3. Move only the coherent group, not unrelated helpers.
4. Keep module import side effects out.
5. Add focused tests or smoke checks for the shared behavior.

## Validation

Use the smallest useful checks:

- `bash -n` for Bash scripts and Bash-sourced helpers.
- `zsh -n` for zsh startup files and zsh-sourced helpers.
- `python -m compileall` for Python tool modules.
- Focused Python unit tests where helper behavior is non-trivial.
- `shellcheck` when available, but do not block on third-party vendored scripts unless they are touched.
- Run changed executable tools in dry-run or harmless modes when possible.
- For helper loading changes, test from the repo checkout and from a temporary copied install tree when practical.
- For migrated Python tools, test launchers from the repo checkout, stowed symlink paths, and temp copied install trees.
