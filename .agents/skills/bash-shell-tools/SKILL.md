---
name: bash-shell-tools
description: Use when adding, updating, reviewing, or refactoring Bash/Zsh shell startup files, sourced shell libraries, dotfiles helper utilities, or executable bin scripts in this dotfiles repo. Applies to `.zshrc`, `.bashrc`, `exports.sh`, aliases, setup scripts, `tools/.local/lib/dotfiles`, `*/bin/*` scripts, and helper promotion from `common.sh` into named modules.
---

# Bash Shell Tools

Use this skill for shell work in this dotfiles repo.

## Required Context

Before editing shell helpers or scripts, read:

- `.agents/rules/bash-first-shell-tools.md`
- `.agents/skills/bash-shell-tools/references/helper-layout.md` when touching helper structure, imports, or `common.sh`

## Workflow

1. Classify the touched file by behavior, not by directory alone:
   - `sourced-startup`: `.zshrc`, `.bashrc`, `exports.sh`
   - `sourced-library`: aliases, helper files, files that are sourced
   - `executable-tool`: `bin` commands like `wally`, `rofi-vpn`, `rofi-cast`
   - `installer-helper`: install/bootstrap/package scripts
2. Preserve the Bash-first rule. Do not introduce Python, Go, TypeScript, Node, or a framework unless the user explicitly asks and the escape-hatch rule is satisfied.
3. Prefer this extraction ladder:
   - keep single-use logic local;
   - extract a private function inside the same file;
   - move repeated helper logic to `common.sh` as an incubator;
   - move coherent helper groups from `common.sh` to a named module.
4. Keep sourced files quiet and safe. They must not print during normal startup, exit the parent shell, start agents, run desktop commands, or require optional tools while being sourced.
5. Keep executable tools explicit. They may print, fail, parse args, and call `require_cmd`, but dependency checks should happen at command execution time, not helper source time.
6. Validate narrowly after edits.

## Sourced Startup Rules

For `.zshrc`, `.bashrc`, `exports.sh`, aliases, and sourced helpers:

- Avoid `exit`; use `return` only when safe for sourced context.
- Avoid `set -euo pipefail` in files that are sourced by an interactive shell.
- Avoid `local` at file scope.
- Guard optional files with `source_if_exists` or explicit `[[ -f ... ]]` checks.
- Use path helpers for PATH mutation instead of repeated `export PATH=...` lines.
- Do not print unless the user requested debug output or an interactive command explicitly runs.

## Executable Tool Rules

For maintained executable Bash tools:

- Use `#!/usr/bin/env bash` unless there is a documented reason not to.
- Prefer `set -Eeuo pipefail` for standalone scripts after confirming current behavior can support it.
- Keep usage/error text consistent through helper functions.
- Use `require_cmd` for runtime dependencies and call it only on paths that need the dependency.
- Keep desktop adapters optional: missing `rofi`, `notify-send`, `dunstify`, `hyprctl`, or `wallust` should fail only for modes that require them.

## Helper Promotion

When moving helpers from `common.sh` to a named module:

1. Identify the first real callers.
2. Choose the nearest behavior name, such as `path.sh`, `source.sh`, `env.sh`, `log.sh`, `command.sh`, `cli.sh`, or `notify.sh`.
3. Move only the coherent group, not unrelated helpers.
4. Update all source/import lines.
5. Keep the old `common.sh` free of dead aliases unless compatibility is needed and documented.
6. Run syntax checks for every touched sourced file and executable script.

## Validation

Use the smallest useful checks:

- `bash -n` for Bash scripts and Bash-sourced helpers.
- `zsh -n` for zsh startup files and zsh-sourced helpers.
- `shellcheck` when available, but do not block on third-party vendored scripts unless they are touched.
- Run changed executable tools in dry-run or harmless modes when possible.
- For helper loading changes, test from the repo checkout and from a temporary copied install tree when practical.
