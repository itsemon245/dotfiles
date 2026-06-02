# Dotfiles Consistency, Decoupling, and Installer Resilience Plan

## Goals

- Make the installer resilient and non-destructive.
- Fix known correctness bugs before structural refactors.
- Support Arch workstation installs as the primary path.
- Support Debian/Fedora server installs with only selected configs and tools.
- Reduce coupling between desktop components, package lists, and shell setup.
- Remove duplication and host-specific state from reusable configs.
- Keep changes incremental so each phase can be reviewed and rolled back.
- Make reusable personal tools installable without requiring the entire dotfiles repo.
- Make startup shell helpers reusable without brittle copy-paste or whole-repo installs.
- Make maintained personal tools readable, testable, and reusable without Bash helper boilerplate.
- Keep the main plan focused on the chosen near-term path: stable language boundaries first, broader distribution ideas later.

## Planning Principles

- Correctness first: destructive stow behavior, broken installer/package logic, syntax errors, and shell startup bugs are fixed before package moves.
- Stable language boundary before moves: keep shell startup helpers separate from maintained executable tools, then package/install around that boundary.
- Sourced shell files matter too: `.zshrc`, `.bashrc`, `exports.sh`, aliases, and sourced setup files should reuse the same small startup-safe helper patterns where appropriate.
- Small reusable helpers only: add a helper when it removes repeated behavior across maintained scripts, not for every small line of shell.
- Tool portability is local first: selective install from this repo comes before any external distribution mechanism.
- Follow the shell/Python boundary rule in `.agents/rules/shell-python-tools.md`: shell remains for startup and tiny wrappers; Python becomes the default for maintained executable tools with shared logic.
- Use the `.agents/skills/shell-python-tools` skill for adding, updating, reviewing, or refactoring shell startup files, sourced helpers, Python dotfiles tools, or thin executable wrappers.
- Deferred implementation ideas belong outside the execution plan until the Python tool model proves insufficient.

## Architecture Decisions

### Problem Statement: Tool Reuse and Language Boundary

The goal is to stop duplicating helper logic while keeping files readable. Phase 2 proved that Bash helpers work for startup files but become noisy for maintained executable tools.

The concrete problems to solve:

- `wally`, `rofi-vpn`, and other executable scripts repeat notification helpers, dependency checks, argument parsing, usage text, and error handling.
- `.zshrc`, `.bashrc`, `exports.sh`, setup scripts, and sourced helper files repeat path handling, guarded sourcing, environment checks, and optional tool setup.
- Bash helper loading for executable tools adds boilerplate and fallback definitions that make tools harder to read.
- Helpers are currently hard to reuse reliably because files live in different stow packages and may be installed without the whole repo.
- A selected tool or shell profile should be usable with only the helper files it needs.

### Shell/Python Language Boundary

This plan follows `.agents/rules/shell-python-tools.md`.

- Shell remains the default for interactive startup files, aliases, sourced environment helpers, and simple installer glue.
- Python becomes the default for maintained executable tools once they need shared logic, structured argument parsing, subprocess orchestration, desktop adapters, cache/temp paths, or tests.
- `uv` is the preferred development/test runner and the runtime for tools that truly need third-party dependencies. Stdlib-only tools should run without network access or dependency resolution at command startup.
- Lua is reserved for app-native Lua contexts such as Neovim unless a specific tool proves it is clearer than Python.
- Interactive shell startup must never depend on Python, uv, Lua, or desktop-only commands.

### Helper Boundary Model

Use separate helper layers instead of forcing every file through one generic library. This boundary is a maintenance rule, not a taxonomy that every new helper must satisfy upfront.

- `shell` helpers are for sourced startup files. They must be safe to source from zsh and bash, avoid exiting the parent shell, avoid printing during normal startup, and avoid desktop-only dependencies.
- Python tool helpers are for maintained executable commands. They can print usage/errors, return non-zero status, use structured modules, and wrap desktop adapters such as notifications, Rofi, Hyprland, Wallust, NetworkManager, and Docker.
- The transitional Bash `tool` helper layer from Phase 2 has been removed. Do not reintroduce it for maintained tools; put reusable executable-tool logic in Python modules.
- Desktop helpers are optional adapters. They should check for commands like `notify-send`, `dunstify`, `rofi`, `hyprctl`, or `wallust` at call time, not while being imported.
- Shared helpers live in a common package only if at least two maintained files use them.
- Files should source helpers relative to their installed location or through a small documented lookup path, not from a hardcoded dotfiles checkout path.

Good first helpers:

- Startup-safe helpers: `path_prepend`, `path_append`, `path_remove`, `path_contains`, `source_if_exists`, `command_exists`, `is_interactive`, and guarded environment setup helpers.
- Python tool helpers: `cli`, `process`, `notify`, `paths`, `rofi`, `wallpaper`, `vpn`, `hypr`, and `php_docker` modules.

A helper earns its place when it removes repeated behavior such as path setup, guarded sourcing, dependency checks, usage printing, notification, temp/cache setup, or dry-run command execution.

### Utility Extraction Workflow

Avoid designing a full utility taxonomy before the code proves it needs one.

1. Keep new logic local when it has one caller.
2. Extract a private function inside the same file when it clarifies that file.
3. Promote to a shared helper only after the behavior appears in at least two maintained files or one file becomes difficult to read without extraction.
4. Place the helper in the nearest cohesive module by behavior, not by abstract category.
5. If no cohesive module exists, create one small module with a plain name and document the first two callers.

Do not create one helper file per tiny function by default. Prefer small cohesive files with a few related functions and no import/source-time side effects.

### Proposed Utility Structure

Use a stow-friendly structure that can also be copied for selective installs:

```text
tools/
  .local/bin/
    wally          # Python executable or tiny launcher
    rofi-vpn       # Python executable or tiny launcher

  .local/lib/dotfiles/
    shell/
      path.sh      # path_prepend, path_append, path_remove, path_contains
      source.sh    # source_if_exists, source_dir_if_exists
      env.sh       # command_exists, is_interactive, has_display
      common.sh    # incubator for startup-safe helpers before they earn a named module

  .local/lib/dotfiles_py/
    dotfiles_tools/
      __init__.py
      cli.py       # argparse helpers, common exit/error behavior
      process.py   # command detection, subprocess wrappers, dry-run support
      notify.py    # dunstify/notify-send/hyprctl notification adapter
      paths.py     # XDG/cache/config/path helpers
      rofi.py      # Rofi menu helpers
      wallpaper.py # wally-specific orchestration helpers
      vpn.py       # NetworkManager/WireGuard helpers
      hypr.py      # Hyprland startup/window helpers
      php_docker.py
```

Keep the structure boring. Python modules should be small and behavior-oriented. Bash `common.sh` is allowed for startup-safe shell helpers, but not as the long-term home for executable tool logic.

### Python Tool Runtime Contract

- Prefer stdlib-only Python for migrated tools. Use `uv` for tests, development commands, and tools that truly need third-party dependencies.
- A migrated command must run from the repo checkout and from a stowed/copied install tree.
- The command entrypoint should be short and obvious: either a direct Python script or a tiny launcher that adds `../lib/dotfiles_py` to `sys.path` and calls `dotfiles_tools.<tool>.main()`.
- Python modules should use `argparse`, `pathlib`, `subprocess.run`, `dataclasses` where useful, and explicit return codes.
- Desktop/system commands remain runtime dependencies and must be checked at the point of use.
- No migrated tool may require network access at startup unless the user explicitly asked that command to perform network work.
- Existing command names and CLI behavior should be preserved unless the plan calls out a deliberate breaking change.

### Package Boundary Model

Create a small personal-tools and shell-helpers area inside the dotfiles repo before extracting anything elsewhere.

Preferred shape:

- Each tool package owns its executable entrypoints, helper files, docs, and dependency metadata.
- Shared startup helpers are separated from executable-script helpers so `.zshrc` and `.bashrc` stay safe and quiet.
- Install/export commands copy or symlink a selected tool plus its declared helper dependencies into `~/.local/bin`, `~/.local/lib/dotfiles`, and `~/.local/lib/dotfiles_py` as needed.
- Stow remains useful for full dotfiles installs, but tool install should not require stowing the whole repo.

### Installer Conflict Policy

Stow and installer conflict handling should be interactive by default and non-destructive unless the user chooses otherwise.

When a target file or directory already exists and would conflict with a stowed file, show the target path and prompt:

- `Y` or `y`: back up this conflict only, then continue.
- `N` or `n`: skip this conflict or package without modifying the target.
- `D` or `d`: delete this conflict and all later conflicts for the current script run.
- `B` or `b`: back up this conflict and all later conflicts for the current script run.

The safe default is backup, not deletion. Dry-runs must never modify files. Non-interactive installs must not delete conflicts unless an explicit conflict policy is provided.

Direct installer removals, such as replacing `~/.zshrc` or `~/.config/pocman`, should use the same prompt/backup behavior instead of unconditional `rm`.

### Profile-Gated Hooks

Tracked configuration files and runtime activation state should stay separate.

Do not track enabled-service symlinks such as `~/.config/systemd/user/*.wants/*.service` as reusable dotfiles. Those symlinks are host activation state: stowing them silently enables services, may point at machine-specific paths, and can enable desktop services during server installs.

Keep actual unit files in the repo when they are reusable. Enable or start them from installer hooks only when the selected profile allows it:

- `server`: no desktop user services.
- `desktop`: generic desktop services only.
- `workstation`: host/workstation services such as speech, input, AppImage, SDDM, OpenRGB, wallpaper, or other local desktop hooks.

Hooks must be listed during dry-run and require confirmation unless `--yes` is explicitly provided.

## Risk Scale

- Low: Small, local, easy to validate, unlikely to break an installed system.
- Medium: Touches install flow, package selection, script behavior, or interactive shell behavior.
- High: Can affect many symlinks, package installs, login/session startup, or user data.

## Progress

| Phase | Status | Notes |
| --- | --- | --- |
| Phase 0 | Complete | Baseline captured in `.phase-0-baseline-2026-05-28.md`. |
| Phase 1 | Complete | Critical safety fixes landed in `9eae85a`: non-destructive stow conflicts, installer delete removal, shell startup fixes, Vim fix, Pocman argument-order fix, and `scripts/check-dotfiles`. |
| Phase 2 | Complete, superseded for executable tools | Shared shell/tool helper structure created and validated; the shell helper layer remains useful for startup files, but the Bash executable-tool helper approach proved too verbose. |
| Phase 2.5 | Complete in current working tree | Maintained commands were re-migrated to Python under `tools/.local/bin` and `tools/.local/lib/dotfiles_py`; old package-local wrappers and the Bash executable-tool helper layer were removed. |
| Phase 3 | Next | Tool package boundaries and selective install can now build on the Python tool runtime contract. |
| Phase 4+ | Pending | Continue after Phase 3 defines selective install boundaries for tools. |

## Phase 0: Baseline and Safety Checks

This phase captures the current state before fixes. It should be fast and should not change behavior.

Status: complete. Captured in `.phase-0-baseline-2026-05-28.md`.

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 0.1 | Capture current `stow -n -v` output for every package and save as a baseline. | Low | Confirm output lists expected packages and known conflicts, especially `obsidian`. |
| 0.2 | Capture current package lists from `pocman/.config/pocman/*.toml`. | Low | Confirm no package list edits occur in this phase. |
| 0.3 | Record maintained shell entrypoints and sourced files: `*/bin/*`, `.zshrc`, `.bashrc`, `exports.sh`, aliases, setup scripts, and files they source. | Low | Produce a simple list used by later syntax checks and helper inventory. |
| 0.4 | Document known generated files and runtime artifacts before changing ignore rules. | Low | Compare against `.gitignore` and `git ls-files`. |

## Phase 1: Critical Bug Fixes and Non-Destructive Safety

This phase fixes known breakage and destructive behavior before any structural refactor. Every later phase depends on safe stow behavior, correct package installation, and clean shell startup.

Status: complete in `9eae85a`.

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 1.1 | Fix `install_arch_with_pm` so it passes `create_type_file=false` before the package name. | High | Run a dry/isolated shell trace or mocked install call and confirm package args are preserved. |
| 1.2 | Replace conflict deletion in `stow.sh` with the interactive conflict policy: prompt per conflict, support one-file backup/skip, and support delete-all or backup-all for the current run. Backups go to `~/.local/state/dotfiles/backups/<timestamp>/`. | High | Create fake file and directory conflicts in a temp HOME and confirm `Y`, `N`, `D`, and `B` behave as documented. |
| 1.3 | Add `--dry-run`, `--packages`, `--except`, and `--adopt` flags to `stow.sh`. | Medium | Run `./stow.sh --dry-run --packages zsh,tmux`; confirm only those packages are checked. |
| 1.4 | Stop hardcoding `cd ~/dotfiles`; resolve the repo root from the script path. | Medium | Run `stow.sh` from outside the repo and confirm package discovery still works. |
| 1.5 | Add internal agent/tooling directories such as `.claude` to `.installignore` so stow does not link them into `$HOME`. | Medium | Dry-run stow and confirm internal dirs are skipped. |
| 1.6 | Fix `zsh/zsh_utils/helpers.sh`: remove invalid `local` declarations at file scope. | Low | Start a new zsh session and confirm no warnings from helpers.sh. |
| 1.7 | Fix `vim/.vimrc`: close the dangling `if has("nvim")` block. | Low | Open vim and confirm no syntax errors on startup. |
| 1.8 | Fix `mac_setup.sh`: replace the nonexistent `source update.sh` reference with the intended stow/setup source. | Low | Run `bash -n mac_setup.sh` and confirm it parses without error. |
| 1.9 | Replace direct destructive installer removals such as `rm -rf ~/.config/pocman` and `rm -f ~/.zshrc` with the same prompt/backup policy used for stow conflicts. | High | Run installer paths against a temp HOME and confirm existing files are backed up, skipped, or deleted only by explicit choice. |
| 1.10 | Fix `exports.sh`: remove duplicate PATH entries, remove duplicate `QT_IM_MODULE=ibus`, and fix `$/usr/local/bin` to `/usr/local/bin`. | Low | Start a new shell and confirm PATH is clean. |
| 1.11 | Remove hardcoded `$HOME/.nvm/versions/node/v20.11.1/bin`; NVM should manage the active Node path. | Low | Confirm `node` still resolves after NVM loads. |
| 1.12 | Remove duplicate NVM loading; keep it in one shell startup path only. | Low | Confirm NVM loads once and `nvm` works. |
| 1.13 | Add a minimal `scripts/check-dotfiles` command for Phase 1 checks: shell syntax, stow dry-run, optional Vim/Neovim/config checks when commands and files exist, and basic path checks. | Medium | Run the command locally and confirm failures are actionable while missing optional commands are reported as skipped. |

## Phase 2: Shared Shell Utilities and Script Debloating

This phase happens before broad package splitting. The aim is to decide the helper model, reduce duplicated shell code, and make sourced startup files and executable scripts consistent while they still live in their current locations.

Status: complete in the current working tree. Inventory captured in `.phase-2-shell-inventory.md`.
Startup-safe shell helpers remain under `tools/.local/lib/dotfiles/shell`; command-style maintained scripts now live under `tools/.local/bin` and are implemented through the Python tool package from Phase 2.5. App-owned desktop config scripts such as Rofi applets, Ironbar states, Sketchybar plugins, OpenRGB/Wallust templates, and SDDM helpers remain with their owning packages and are covered by validation.

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 2.1 | Inventory `zsh`, possible Bash startup files, aliases, setup scripts, `hyprland/bin`, `customization/scripts`, `others/env/bin`, and installer scripts. | Low | Classify each maintained file as `sourced-startup`, `sourced-library`, `portable-tool`, `desktop-tool`, `installer-helper`, or `one-off`. |
| 2.2 | Identify duplicated behavior across maintained files: path setup, guarded sourcing, interactive-shell checks, optional command setup, notification, logging, `die`, `require_cmd`, usage text, temp/cache paths, and dry-run command execution. | Low | List only helpers used by at least two maintained files. |
| 2.3 | Historical Phase 2 choice: adopt a Bash-first helper pilot. This is now superseded for maintained executable tools by the shell/Python boundary in Phase 2.5. | Low | Phase 2.5 updates `.agents/rules/shell-python-tools.md` and skill guidance so Python is the default for reusable executable tools. |
| 2.4 | Create the initial startup-safe helper modules: `shell/path.sh`, `shell/source.sh`, and `shell/env.sh`. | Medium | Source helpers from zsh and bash; confirm they do not print, exit, mutate unrelated state, or require desktop commands at load time. |
| 2.5 | Historical Phase 2 choice: create an initial Bash executable-tool helper layer. This layer has now been removed after the Python remigration. | Medium | `rg` confirms no maintained Python tool imports `tools/.local/lib/dotfiles/tool`. |
| 2.6 | Define the helper loading contract for both layers without building a large framework. | Medium | A sourced startup file and a pilot executable can run from the repo checkout and from a copied temp install tree. |
| 2.7 | Apply startup helpers first to `exports.sh`, `.zshrc`, and any sourced shell files with repeated PATH/source logic. | Medium | Start a new zsh session and confirm PATH, NVM, aliases, and optional sources behave as before with less duplication and without noisy startup output. |
| 2.8 | Historical Bash pilot: update `wally` and `rofi-vpn` to use shared Bash helpers. This proved helper-loading overhead was not acceptable for real tools. | Medium | Superseded by Phase 2.5 Python smoke checks. |
| 2.9 | Historical Bash refactor of `wally`. The behavior has now moved into `dotfiles_tools.wallpaper`. | Medium | Test picker mode, direct `set`, no-upscale, optional upscale, and missing dependency handling through `tools/.local/bin/wally`. |
| 2.10 | Historical Bash refactor target for Rofi tools. These tools now use Python modules and launchers. | Medium | `rofi-cast`, `rofi-monitor`, and similar tools pass `--help` or dry-run checks from `tools/.local/bin`. |
| 2.11 | DRY the PHP/Composer Docker wrappers by moving shared setup into `dotfiles_tools.php_docker`; remove `others/env/bin` wrappers. | Low | `php`, `composer`, and `sysphp` smoke-test through internal tool help; normal use still resolves through `tools/.local/bin`. |
| 2.12 | Add validation for maintained files: `bash -n`, `zsh -n` where appropriate, `shellcheck` when available, optional Vim/Neovim/config validation when commands and files exist, and mocked dry-runs for commands that call system tools. | Medium | `scripts/check-dotfiles` reports startup-helper, tool-helper, and config failures clearly; unavailable optional validators are skipped. |
| 2.13 | Migrate maintained first-party command locations into `tools/.local/bin`, update known call sites to the canonical commands, and remove old package-local wrappers instead of keeping compatibility shims. | High | `scripts/check-dotfiles` passes; stow dry-runs confirm new paths; Hyprland keybinds, Waybar/Ironbar commands, Rofi launchers, installer calls, and shell startup all resolve the migrated commands/helpers. |

## Phase 2.5: Python Tool Runtime and Re-Migration

Phase 2.5 corrects the Phase 2 overreach. The shell helper model remains for sourced startup files, but maintained executable tools should move to Python when they need reusable logic, structured parsing, desktop adapters, subprocess orchestration, or tests.

Status: complete in the current working tree. `scripts/check-dotfiles` passed after the Python migration and old-wrapper removal.

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 2.5.1 | Audit the Phase 2 migrated commands and classify each as `python-tool`, `tiny-shell-wrapper`, `sourced-startup`, `installer-shell`, or `app-owned-script`. | Low | Update `.phase-2-shell-inventory.md` with the final language target for each maintained file. |
| 2.5.2 | Add the Python tool layout under `tools/.local/lib/dotfiles_py/dotfiles_tools` with `__init__.py` and small stdlib-first modules. | Medium | `python -m compileall tools/.local/lib/dotfiles_py` passes without importing desktop commands. |
| 2.5.3 | Define the launcher contract for `tools/.local/bin`: commands either run as direct Python scripts or tiny launchers that add `../lib/dotfiles_py` to `sys.path` and call a module `main()`. | Medium | A launcher works from the repo checkout, through a stowed symlink, and from a copied temp install tree. |
| 2.5.4 | Add shared Python modules for common behavior: `cli`, `process`, `notify`, `paths`, `rofi`, `wallpaper`, `vpn`, `hypr`, and `php_docker` as needed. | Medium | Unit/smoke tests cover command detection, dry-run execution, notification fallback, Rofi input formatting, and path/cache handling. |
| 2.5.5 | Re-migrate `wally` first as the desktop orchestration pilot: preserve CLI behavior, no source wallpaper deletion, optional Rofi/upscale/theme/reload behavior, and no network/runtime dependency resolution. | High | Test `--help`, direct `set`, missing dependency handling, no-upscale path, and dry-run/no-op paths without changing the current desktop state. |
| 2.5.6 | Re-migrate `rofi-vpn` after `wally`: preserve import/remove/toggle behavior, require `rofi` only for picker flows, and keep `nmcli` checks at runtime. | High | Test `--help`, `--version`, import argument parsing against temp config names, missing `nmcli` handling, and picker dependency gates. |
| 2.5.7 | Re-migrate smaller desktop tools: `rofi-cast`, `rofi-monitor`, `barr`, `brightness`, `brightness-adjust`, `cliphist-rofi`, and `readable-window` where Python makes them shorter or clearer. | Medium | Canonical command names work; `--help` or harmless smoke checks pass; desktop-only actions are guarded or dry-run tested. |
| 2.5.8 | Re-migrate portable tools and wrappers: `zstd-compress`, `zstd-extract`, `memory`, `download_speed`, `php`, `composer`, and `sysphp` where Python improves clarity. Keep truly tiny wrappers in shell. | Medium | Smoke tests cover argument parsing and dependency checks without compressing/extracting user data or starting containers. |
| 2.5.9 | Move Hyprland startup orchestration to `tools/.local/bin/hypr-startup` backed by `dotfiles_tools.hypr`, then update `hyprland.conf` to call it directly and remove `startup/launch.sh`. | High | Dry-run or mocked startup confirms intended commands, log file paths, dependency skips, and no duplicate service starts. |
| 2.5.10 | Remove the Bash executable-tool helper layer after migrated tools no longer use it. Keep startup-safe `shell` helpers. | Medium | `rg` confirms no migrated Python tool depends on `tools/.local/lib/dotfiles/tool`; no legacy wrappers are required because known call sites use canonical commands. |
| 2.5.11 | Expand validation for Python tools: compile checks, focused unit tests where useful, `--help` smoke tests, temp HOME/stow wrapper checks, and existing shell startup checks. | Medium | `scripts/check-dotfiles` reports Python syntax/test failures clearly while optional validators are skipped when unavailable. |
| 2.5.12 | Update docs and agent guidance after the migration proves the Python structure. | Low | Plan, rules, skill references, and README agree on Bash for startup/wrappers and Python for maintained tools. |

## Phase 3: Tool Package Boundaries and Selective Install

This phase makes selected tools installable without the whole dotfiles repo. It follows Phase 2.5 because the Python tool runtime contract needs to exist before install/export logic can be correct.

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 3.1 | Create the dedicated `tools/` stow package for stable personal tools and shared helper layers. | Medium | `stow -n tools` or equivalent dry-run shows intended `~/.local/bin`, `~/.local/lib/dotfiles/shell`, and `~/.local/lib/dotfiles_py` links. |
| 3.2 | Define lightweight per-tool metadata listing executable files, helper dependencies, runtime commands, and profile tags. | Medium | `scripts/install-tool --dry-run wally` prints exactly which files and commands are required. |
| 3.3 | Add `scripts/install-tool <name>` for selective local installs into `~/.local/bin`, `~/.local/lib/dotfiles`, and `~/.local/lib/dotfiles_py`, with `--dry-run` and `--prefix`. | Medium | Install only `wally` or only `rofi-vpn` into a temp prefix and confirm no unrelated dotfiles package is copied. |
| 3.4 | Keep full stow packages for normal dotfiles setup, but make Python tool packages usable without full stow. | Medium | `./stow.sh --packages tools --dry-run` and `scripts/install-tool --dry-run <name>` both describe valid, non-conflicting installs. |
| 3.5 | Document the difference between full stow, shell-helper sourcing, and selective tool install. | Low | A new machine can install one selected command without following the full workstation install flow. |

## Phase 4: `pocman` and Installer Resilience

This phase finishes package-manager correctness after the critical argument-order bug is fixed. It should happen before install profiles because profiles need reliable package resolution and dry-runs.

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 4.1 | Batch install packages by package manager in `install_all_from_toml` instead of looping one package at a time. | Medium | Confirm `pacman`, `yay`, `paru`, `apt`, and `dnf` groups are parsed correctly. |
| 4.2 | Add `--dry-run` to `pocman` so it prints package groups without installing. | Medium | Run `pocman --all --only=cli --dry-run` on Arch and confirm no install command executes. |
| 4.3 | Stop mutating TOML files during `--all` installs; only mutate on explicit `pocman install <pkg>` operations. | Medium | Run `git diff` after `--all --dry-run` and after mocked install flows. |
| 4.4 | Split TOML parsing and package installation into smaller sourced files under `pocman/lib`. | Medium | Run `bash -n` and current command examples after each extraction. |
| 4.5 | Change `install.sh` to accept `--dry-run`, `--no-packages`, and explicit confirmation behavior before profile expansion. | High | Run dry-runs and confirm no packages are installed or stow changes are made. |
| 4.6 | Add an explicit `--yes` flag for non-interactive installs. | Medium | Confirm unattended install exits if confirmation would be required and `--yes` is absent. |

## Phase 5: Install Profiles

Profiles come after the installer and package manager have dry-run support. This avoids encoding broken behavior into multiple install paths.

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 5.1 | Create profile definitions: `base`, `server`, `desktop`, `workstation`, and optional `gaming`. | Medium | Print each profile and confirm intended packages/stow packages are included. |
| 5.2 | Change `install.sh` to accept `--profile`, `--only`, and `--except`. | High | Run dry-runs for Arch workstation and Debian/Fedora server paths. |
| 5.3 | Make `server` install only portable packages: shell, tmux, nvim, git, basic CLI tools, and selected scripts. | Medium | Dry-run `--profile server`; confirm no Hyprland, SDDM, Waybar, Rofi, Qt, or gaming packages. |
| 5.4 | Make `desktop` include desktop config without host-specific extras. Desktop-owned components include Hyprland, Waybar, Rofi, Wallust, Dunst, Ironbar, Wlogout, ReGreet, shared theme assets, OpenRGB theming, MangoHud theming, and SDDM config/templates. | Medium | Dry-run `--profile desktop`; confirm desktop packages are included without workstation-only hooks. |
| 5.5 | Make `workstation` the only profile that runs desktop hooks such as SDDM, Hyprland, fonts, wallpaper tooling, and optional local apps. | High | Dry-run `--profile workstation`; confirm hooks are listed but not run unless selected. |
| 5.6 | Move systemd user-service activation out of tracked `.wants` symlinks and into profile-gated hooks. Keep reusable unit files tracked, but enable/start services only from allowed profiles. | High | Dry-run each profile and confirm server does not enable desktop services; workstation lists intended user-service hooks. |
| 5.7 | Add a `bootstrap-server.sh` one-liner for headless servers: `curl -sL <url> \| bash` clones repo shallowly and runs `./install.sh --profile server`. | Low | Test on a clean container to confirm zsh, git, nvim, and tmux are configured. |

## Phase 6: Shell and Server Portability

This phase applies the Phase 2 shell-helper model more broadly after immediate bugs are fixed and profiles exist. Keep interactive shell startup independent from desktop-only tools.

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 6.1 | Replace remaining duplicated PATH exports with the shared `path_prepend` and `path_append` helpers; use shell-native deduplication where appropriate. | Medium | Start a new zsh and bash shell where applicable; confirm no duplicate PATH entries or missing tool paths. |
| 6.2 | Remove host-specific `/Users/emon`, `/home/emon`, `~/dotfiles`, and `~/scripts` assumptions from reusable startup files and app configs. Use `$HOME`, XDG paths, repo-root detection, commands from `PATH`, or local/workstation-only files. | Medium | Run a repo-wide host-path scan; start zsh on Linux and macOS-style path checks without errors; confirm desktop configs still resolve scripts and assets. |
| 6.3 | Load NVM in one place only and make it optional. | Medium | Confirm shell startup works with and without `~/.nvm`. |
| 6.4 | Replace `zsh-setup.sh` repeated git clones with idempotent clone-or-update logic. | Medium | Run twice and confirm no failures if plugins already exist. |
| 6.5 | Stop starting a new `ssh-agent` on every shell startup; reuse an existing agent or make it opt-in. | Medium | Open multiple shells and confirm agent count does not grow. |
| 6.6 | Remove runtime `chmod -R` from `.zshrc`; store executable bits in git instead. | Low | Confirm aliases and sourced files still load. |
| 6.7 | Guard all `source` calls in startup files with shared `source_if_exists` or equivalent checks. | Medium | Start zsh with a missing optional file and confirm no errors. |
| 6.8 | Standardize shebangs to `#!/usr/bin/env bash` for remaining maintained Bash scripts and tiny wrappers, with documented exceptions for curl-piped scripts. | Low | Run shell syntax checks on all maintained scripts after the change. |

## Phase 7: Split Desktop Packages by Ownership

Package splitting now happens after bugs, shared utilities, selective tool install, and profiles. That order is safer because files move only after their runtime contracts are clearer.

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 7.1 | Split `hyprland/.config/waybar` into a top-level `waybar/` stow package. | High | `stow -n hyprland waybar`; confirm target paths do not conflict. |
| 7.2 | Split `hyprland/.config/rofi` into top-level `rofi/`. | High | Test launcher paths and Hyprland keybinds after stowing. |
| 7.3 | Split `hyprland/.config/wallust` into top-level `wallust/`. | High | Run `wallust run <image>` and confirm all generated targets update. |
| 7.4 | Split notification config/templates into `dunst/` if current generated config is intended to be managed independently. | Medium | Confirm `dunst` starts and receives generated colors. |
| 7.5 | Keep Ironbar, Wlogout, ReGreet, shared desktop themes, OpenRGB theming, MangoHud theming, Wallust templates, and SDDM theming in desktop-owned packages, either as one coherent desktop package or smaller packages split by ownership. | Medium | Dry-run desktop/workstation profiles and confirm these components are never pulled into base/server profiles. |
| 7.6 | Keep `wally` and other stable desktop helper commands in `tools` or move them to `desktop-tools` according to the Phase 3 package boundary. | Medium | Confirm `~/.local/bin/wally` exists after stow or selective install and `SUPER+W` still works. |

## Phase 8: Desktop Runtime Dependency Reduction

This phase completes desktop script decoupling after Python tool helpers and install profiles exist. It should mostly apply the Python desktop adapters from Phase 2.5.

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 8.1 | Add wallpaper backend adapter behavior to `wally`: prefer configured backend, support `swww`, `awww`, or no-op theme generation. | Medium | Test with installed backend and dry-run/no-op mode. |
| 8.2 | Require `rofi` only for picker mode, not direct `wally set <image>`. | Low | Run direct set on a minimal system without Rofi. |
| 8.3 | Require `realesrgan-ncnn-vulkan` only when `--upscale` is used. | Low | Run normal wallpaper set without the upscaler installed. |
| 8.4 | Wrap reloads for Waybar, Dunst, Kitty, Qt, GTK, OpenRGB, and Hyprland in `command -v` or process checks. | Medium | Run on a partial desktop and confirm missing tools do not abort the script. |
| 8.5 | Replace `go run ~/scripts/netspeed.go` in Waybar with a maintained script or compiled helper that does not spawn Go every interval. | Medium | Confirm Waybar shows speed and no Go process starts every interval. |
| 8.6 | Move inline Waybar command pipelines for memory/music into scripts under the appropriate package. | Low | Run each script directly and confirm expected output. |
| 8.7 | Gate optional Waybar modules behind package/profile choices. | Medium | Server/base profile should not require Waybar dependencies. |
| 8.8 | Continue hardening `hypr-startup` so optional autostart commands are host/profile-aware and missing commands are quiet. | Medium | Start Hyprland with missing optional apps and confirm no noisy failures. |
| 8.9 | Move Slack/LocalSend autostart to a host/workstation-specific hook. | Low | Confirm workstation profile can enable them, desktop profile can skip them. |

## Phase 9: Repository Hygiene and Generated Artifacts

This phase reduces tracked state and repo weight. It should be done after safety checks exist because some steps can affect many tracked files.

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 9.1 | Remove or ignore tracked runtime artifacts: qBittorrent state, backups, shell history, OpenRGB logs, and local `.env` files. | Medium | Confirm examples remain, secrets/state are untracked, and app configs still have templates. |
| 9.2 | Remove the large game archive from the repo and add archive patterns to `.gitignore`. | Medium | Confirm repository size decreases after history cleanup if that is chosen. |
| 9.3 | Replace vendored `zsh/.oh-my-zsh` with bootstrap-managed install or git submodules. | High | Fresh install must still produce a working Zsh setup; offline expectations should be documented. |
| 9.4 | Decide whether fonts are repo assets or package-managed dependencies; avoid doing both for the same font family. | Medium | Confirm fontconfig and Waybar/Kitty font names resolve after install. |
| 9.5 | Ensure generated Wallust outputs are ignored consistently and only templates are tracked. | Low | Run `wallust run` and confirm generated color files do not appear in `git status`. |
| 9.6 | Remove nested `.git` directories from vendored zsh plugins (`zsh-autosuggestions/.git`, `zsh-syntax-highlighting/.git`). | Low | Confirm plugins still load correctly without their `.git` dirs. |
| 9.7 | Consider replacing Oh My Zsh entirely with direct plugin loading after all other shell changes are stable. | High | Full `.zshrc` rewrite; requires custom prompt or starship and a fresh-login test. |

## Phase 10: Validation and Documentation

Documentation should be updated incrementally, but this final phase makes sure the full refactor is understandable from a fresh machine.

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 10.1 | Update `README.md` and `AGENTS.md` to match actual package layout after splitting. | Low | Read install examples and confirm paths exist. |
| 10.2 | Add a quickstart for Arch workstation, Debian server, and Fedora server. | Low | Copy commands into shell with `--dry-run` and confirm they parse. |
| 10.3 | Add recovery docs for stow conflicts and backup restore. | Low | Confirm backup path and restore command examples match implementation. |
| 10.4 | Add a smoke-test checklist for a new machine. | Low | Run checklist on current machine after refactor. |
| 10.5 | Document selective tool install and helper dependency rules. | Low | A reader can install one selected tool without stowing the full repo. |
| 10.6 | Keep shell syntax checks for all maintained Bash/Zsh scripts and optional Vim/Neovim/config checks in the standard validation command. | Medium | Run checks locally, skip unavailable optional validators cleanly, and handle known third-party scripts separately. |

## Recommended Iteration Order

1. Phase 0 first, to establish a baseline before any changes.
2. Phase 1 next, because major bugs and destructive behavior must be fixed before refactors.
3. Phase 2 is complete as a shell helper/path migration, but its Bash executable-helper approach is superseded.
4. Phase 2.5 is complete in the current working tree; keep validating migrated tools as they are used.
5. Phase 3 next, because selective tool install depends on the Python runtime contract from Phase 2.5.
6. Phase 4 next, because package-manager correctness affects install profiles.
7. Phase 5 next, so profiles define package and stow boundaries before desktop splits.
8. Phase 6 can proceed after profiles exist, with shell startup kept independent from desktop-only tools.
9. Phase 7 should be done in small commits: one stow package split at a time.
10. Phase 8 applies the Python desktop adapter model to desktop runtime scripts and bars.
11. Phase 9 should be done carefully, especially if removing tracked large files or vendored Oh My Zsh.
12. Phase 10 happens continuously for touched areas, then gets a final pass at the end.

## First Concrete PR Scope

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| A | Fix `install_arch_with_pm` argument order. | High | Mock or dry-run package install path. |
| B | Replace stow conflict deletion with the interactive conflict policy: per-conflict backup/skip and runtime delete-all/backup-all choices. | High | Test fake file and directory conflicts under temp HOME. |
| C | Add `--dry-run` and package selection flags to `stow.sh`. | Medium | Confirm no filesystem changes occur in dry-run mode. |
| D | Fix `helpers.sh` invalid `local` at file scope. | Low | Start zsh, confirm no warnings. |
| E | Fix `.vimrc` dangling `if has("nvim")` block. | Low | Open vim, confirm no errors. |
| F | Fix `mac_setup.sh` nonexistent `source update.sh`. | Low | `bash -n mac_setup.sh` passes. |
| G | Replace direct destructive installer removals with prompt/backup behavior. | High | Temp HOME install path preserves existing files unless deletion is explicitly selected. |
| H | Fix `exports.sh` duplicates, typo, hardcoded NVM path, and duplicate NVM loading. | Low | New shell has clean PATH and NVM loads once. |
| I | Add internal dirs such as `.claude` to `.installignore`. | Low | Confirm stow dry-run skips them. |
| J | Add or update the first `scripts/check-dotfiles` safety command, including optional Vim/Neovim/config checks when available. | Medium | Command runs Phase 1 validations locally and skips unavailable optional validators. |
| K | Document the new safety behavior. | Low | Confirm README/plan examples match commands. |

## Second Concrete PR Scope

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| A | Inventory maintained shell entrypoints, sourced files, and duplicated helper behavior. | Low | Produce the script/helper table. |
| B | Create the startup-safe shell helper layer. | Medium | Source helpers from zsh and bash with no load-time side effects. |
| C | Create the Bash tool helper layer as a temporary pilot. This implementation is now superseded for maintained executable tools. | Medium | Source helpers from Bash with no load-time side effects. |
| D | Apply path/source helpers to `exports.sh`, `.zshrc`, and sourced shell files. | Medium | New shell has clean PATH and missing optional files do not error. |
| E | Migrate `wally` and `rofi-vpn` as Bash executable pilot scripts. This proved the helper-loading overhead is not acceptable for real tools. | Medium | Both scripts run from repo checkout and temp install tree. |
| F | Add shell and optional config validation for maintained files. | Medium | `scripts/check-dotfiles` reports syntax/helper/config issues clearly and skips unavailable optional validators. |
| G | Move maintained command locations into `tools/.local/bin`, update known callers, and remove old package-local wrappers once the Python runtime is in place. | High | All known script entrypoints resolve from their new locations and `scripts/check-dotfiles` passes. |

## Recent Concrete PR Scope: Python Tool Runtime And Wrapper Removal

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| A | Add `tools/.local/lib/dotfiles_py/dotfiles_tools` with `__init__.py`, `cli.py`, `process.py`, `notify.py`, and `paths.py`. | Medium | `python -m compileall tools/.local/lib/dotfiles_py` passes. |
| B | Add launcher helpers or a tiny launcher pattern for `tools/.local/bin` commands. | Medium | Launcher works from repo checkout, stowed symlink path, and temp copied install tree. |
| C | Re-migrate `wally` to Python as the first pilot. | High | `wally --help`, direct set argument resolution, missing dependency gates, and no-op/dry-run paths pass without changing live wallpaper. |
| D | Re-migrate `rofi-vpn` to Python after the pilot structure is proven. | High | `rofi-vpn --help`, `--version`, import parsing, missing `nmcli`, and picker dependency gates pass. |
| E | Re-migrate the remaining maintained desktop and portable tools, including PHP/Composer wrappers and Hyprland startup. | High | `--help`, internal help, compile checks, and dry-runs validate command entrypoints without changing VPNs, containers, archives, or the live desktop. |
| F | Update known call sites to `~/.local/bin` and remove old package-local wrappers. | Medium | `rg` confirms Hyprland, Waybar, Ironbar, and docs no longer call old locations. |
| G | Update `scripts/check-dotfiles` for Python compile/smoke tests and keep existing shell startup checks. | Medium | Validation reports Python failures clearly and keeps shell alias/source regressions covered. |
| H | Update inventory/docs after the Python migration. | Low | Plan, skills, and inventory agree on the shell/Python boundary. |
