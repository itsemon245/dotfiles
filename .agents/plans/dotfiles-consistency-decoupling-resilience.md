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
- Make atomic shell helpers reusable without brittle copy-paste or whole-repo installs.
- Keep the main plan focused on the chosen near-term path: shared shell utilities first, broader distribution ideas later.

## Planning Principles

- Correctness first: destructive stow behavior, broken installer/package logic, syntax errors, and shell startup bugs are fixed before package moves.
- Shared utilities before moves: decide how shell helpers are shared and pilot them in real files before splitting more packages or rewriting tools.
- Sourced shell files matter too: `.zshrc`, `.bashrc`, `exports.sh`, aliases, setup scripts, and executable `bin` scripts should reuse the same small helper patterns where appropriate.
- Small reusable helpers only: add a helper when it removes repeated behavior across maintained scripts, not for every small line of shell.
- Tool portability is local first: selective install from this repo comes before any external distribution mechanism.
- Follow the Bash-first rule in `.agents/rules/bash-first-shell-tools.md`: stay in Bash unless a Python+uv refactor clearly makes a tool smaller, clearer, and easier to maintain.
- Use the `.agents/skills/bash-shell-tools` skill for adding, updating, reviewing, or refactoring shell startup files, sourced helpers, and executable shell tools.
- Deferred implementation ideas belong outside the execution plan until the shared shell utility model proves insufficient.

## Architecture Decisions

### Problem Statement: Atomic Shell Reuse

The goal is to stop duplicating small shell helpers across both executable scripts and sourced startup files.

The concrete problems to solve:

- `wally`, `rofi-vpn`, and other executable scripts repeat notification helpers, dependency checks, argument parsing, usage text, and error handling.
- `.zshrc`, `.bashrc`, `exports.sh`, setup scripts, and sourced helper files repeat path handling, guarded sourcing, environment checks, and optional tool setup.
- Helpers are currently hard to reuse reliably because files live in different stow packages and may be installed without the whole repo.
- A selected tool or shell profile should be usable with only the helper files it needs.

### Bash-First Rule

This plan follows `.agents/rules/bash-first-shell-tools.md`. Bash remains the default for shell startup helpers and executable shell tools so the repository does not grow duplicate helper stacks in multiple languages.

A Bash tool can move to Python only as an escape hatch: the Python+uv version must be smaller or clearer, must run like a normal `bin` command through its shebang, and must not make interactive shell startup depend on Python.

### Helper Boundary Model

Use two helper layers instead of forcing every shell file through one generic library. This boundary is a maintenance rule, not a taxonomy that every new helper must satisfy upfront.

- `shell` helpers are for sourced startup files. They must be safe to source from zsh and bash, avoid exiting the parent shell, avoid printing during normal startup, and avoid desktop-only dependencies.
- `tool` helpers are for executable Bash scripts. They can assume Bash, can print usage/errors, can return non-zero status, and can wrap desktop adapters such as notifications.
- Desktop helpers are optional adapters. They should check for commands like `notify-send`, `dunstify`, `rofi`, `hyprctl`, or `wallust` at call time, not while being sourced.
- Shared helpers live in a common package only if at least two maintained files use them.
- Files should source helpers relative to their installed location or through a small documented lookup path, not from a hardcoded dotfiles checkout path.

Good first helpers:

- Startup-safe helpers: `path_prepend`, `path_append`, `path_remove`, `path_contains`, `source_if_exists`, `command_exists`, `is_interactive`, and guarded environment setup helpers.
- Tool helpers: `die`, `warn`, `info`, `usage`, `require_cmd`, `run`, `confirm`, `dry_run`, temp/cache path helpers, and `notify`.

A helper earns its place when it removes repeated behavior such as path setup, guarded sourcing, dependency checks, usage printing, notification, temp/cache setup, or dry-run command execution.

### Utility Extraction Workflow

Avoid designing a full utility taxonomy before the code proves it needs one.

1. Keep new logic local when it has one caller.
2. Extract a private function inside the same file when it clarifies that file.
3. Promote to a shared helper only after the behavior appears in at least two maintained files or one file becomes difficult to read without extraction.
4. Place the helper in the nearest cohesive module by behavior, not by abstract category.
5. If no cohesive module exists, create one small module with a plain name and document the first two callers.

Do not create one helper file per tiny function by default. Prefer small cohesive files with a few related functions and no source-time side effects.

### Proposed Utility Structure

Use a stow-friendly structure that can also be copied for selective installs:

```text
tools/
  .local/bin/
    wally
    rofi-vpn

  .local/lib/dotfiles/
    shell/
      path.sh      # path_prepend, path_append, path_remove, path_contains
      source.sh    # source_if_exists, source_dir_if_exists
      env.sh       # command_exists, is_interactive, has_display
      common.sh    # incubator for startup-safe helpers before they earn a named module
    tool/
      log.sh       # info, warn, die
      command.sh   # require_cmd, run, dry_run
      cli.sh       # usage helpers and argument helper conventions
      notify.sh    # notify adapter with command checks at call time
      common.sh    # incubator for executable-tool helpers before they earn a named module
```

Keep the structure boring. `common.sh` is allowed as an incubator, not a dumping ground. If it grows large or a group of functions becomes coherent, move that group into a named module.

### Package Boundary Model

Create a small personal-tools and shell-helpers area inside the dotfiles repo before extracting anything elsewhere.

Preferred shape:

- Each tool package owns its executable entrypoints, helper files, docs, and dependency metadata.
- Shared startup helpers are separated from executable-script helpers so `.zshrc` and `.bashrc` stay safe and quiet.
- Install/export commands copy or symlink a selected tool plus its declared helper dependencies into `~/.local/bin` and `~/.local/lib/dotfiles`.
- Stow remains useful for full dotfiles installs, but tool install should not require stowing the whole repo.

## Risk Scale

- Low: Small, local, easy to validate, unlikely to break an installed system.
- Medium: Touches install flow, package selection, script behavior, or interactive shell behavior.
- High: Can affect many symlinks, package installs, login/session startup, or user data.

## Phase 0: Baseline and Safety Checks

This phase captures the current state before fixes. It should be fast and should not change behavior.

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 0.1 | Capture current `stow -n -v` output for every package and save as a baseline. | Low | Confirm output lists expected packages and known conflicts, especially `obsidian`. |
| 0.2 | Capture current package lists from `pocman/.config/pocman/*.toml`. | Low | Confirm no package list edits occur in this phase. |
| 0.3 | Record maintained shell entrypoints and sourced files: `*/bin/*`, `.zshrc`, `.bashrc`, `exports.sh`, aliases, setup scripts, and files they source. | Low | Produce a simple list used by later syntax checks and helper inventory. |
| 0.4 | Document known generated files and runtime artifacts before changing ignore rules. | Low | Compare against `.gitignore` and `git ls-files`. |

## Phase 1: Critical Bug Fixes and Non-Destructive Safety

This phase fixes known breakage and destructive behavior before any structural refactor. Every later phase depends on safe stow behavior, correct package installation, and clean shell startup.

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 1.1 | Fix `install_arch_with_pm` so it passes `create_type_file=false` before the package name. | High | Run a dry/isolated shell trace or mocked install call and confirm package args are preserved. |
| 1.2 | Replace conflict deletion in `stow.sh` with timestamped backup to `~/.local/state/dotfiles/backups/<timestamp>/`. | High | Create a fake conflict in a temp HOME and confirm it is backed up, not deleted. |
| 1.3 | Add `--dry-run`, `--packages`, `--except`, and `--adopt` flags to `stow.sh`. | Medium | Run `./stow.sh --dry-run --packages zsh,tmux`; confirm only those packages are checked. |
| 1.4 | Stop hardcoding `cd ~/dotfiles`; resolve the repo root from the script path. | Medium | Run `stow.sh` from outside the repo and confirm package discovery still works. |
| 1.5 | Add internal agent/tooling directories such as `.claude` to `.installignore` so stow does not link them into `$HOME`. | Medium | Dry-run stow and confirm internal dirs are skipped. |
| 1.6 | Fix `zsh/zsh_utils/helpers.sh`: remove invalid `local` declarations at file scope. | Low | Start a new zsh session and confirm no warnings from helpers.sh. |
| 1.7 | Fix `vim/.vimrc`: close the dangling `if has("nvim")` block. | Low | Open vim and confirm no syntax errors on startup. |
| 1.8 | Fix `mac_setup.sh`: replace the nonexistent `source update.sh` reference with the intended stow/setup source. | Low | Run `bash -n mac_setup.sh` and confirm it parses without error. |
| 1.9 | Fix `exports.sh`: remove duplicate PATH entries, remove duplicate `QT_IM_MODULE=ibus`, and fix `$/usr/local/bin` to `/usr/local/bin`. | Low | Start a new shell and confirm PATH is clean. |
| 1.10 | Remove hardcoded `$HOME/.nvm/versions/node/v20.11.1/bin`; NVM should manage the active Node path. | Low | Confirm `node` still resolves after NVM loads. |
| 1.11 | Remove duplicate NVM loading; keep it in one shell startup path only. | Low | Confirm NVM loads once and `nvm` works. |
| 1.12 | Add a minimal `scripts/check-dotfiles` command for Phase 1 checks: shell syntax, stow dry-run, and basic path checks. | Medium | Run the command locally and confirm failures are actionable. |

## Phase 2: Shared Shell Utilities and Script Debloating

This phase happens before broad package splitting. The aim is to decide the helper model, reduce duplicated shell code, and make sourced startup files and executable scripts consistent while they still live in their current locations.

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 2.1 | Inventory `zsh`, possible Bash startup files, aliases, setup scripts, `hyprland/bin`, `customization/scripts`, `others/env/bin`, and installer scripts. | Low | Classify each maintained file as `sourced-startup`, `sourced-library`, `portable-tool`, `desktop-tool`, `installer-helper`, or `one-off`. |
| 2.2 | Identify duplicated behavior across maintained files: path setup, guarded sourcing, interactive-shell checks, optional command setup, notification, logging, `die`, `require_cmd`, usage text, temp/cache paths, and dry-run command execution. | Low | List only helpers used by at least two maintained files. |
| 2.3 | Adopt the Bash-first rule from `.agents/rules/bash-first-shell-tools.md`. | Low | Confirm Python is documented only as an escape hatch for tools that become smaller and clearer after refactor. |
| 2.4 | Create the initial startup-safe helper modules: `shell/path.sh`, `shell/source.sh`, and `shell/env.sh`. | Medium | Source helpers from zsh and bash; confirm they do not print, exit, mutate unrelated state, or require desktop commands at load time. |
| 2.5 | Create the initial executable-tool helper modules: `tool/log.sh`, `tool/command.sh`, `tool/cli.sh`, and `tool/notify.sh`. | Medium | Source helpers from Bash; confirm helper load has no side effects and functions fail clearly when dependencies are missing. |
| 2.6 | Define the helper loading contract for both layers without building a large framework. | Medium | A sourced startup file and a pilot executable can run from the repo checkout and from a copied temp install tree. |
| 2.7 | Apply startup helpers first to `exports.sh`, `.zshrc`, and any sourced shell files with repeated PATH/source logic. | Medium | Start a new zsh session and confirm PATH, NVM, aliases, and optional sources behave as before with less duplication and without noisy startup output. |
| 2.8 | Update only two executable pilot scripts first, `wally` and `rofi-vpn`, to use shared helpers and consistent usage/error output. | Medium | Existing flows still work and duplicated helper code is removed from both scripts. |
| 2.9 | Refactor `wally` in place after the pilot: dependency gates, no source wallpaper deletion, optional Rofi/upscale/reload behavior, and cleaner function boundaries. | Medium | Test picker mode, direct `set`, no-upscale, optional upscale, and missing dependency handling. |
| 2.10 | Refactor remaining thin Rofi scripts only after the pilot proves the helper contract. | Medium | `rofi-cast`, `rofi-monitor`, and similar scripts share helper behavior without gaining large abstractions. |
| 2.11 | DRY the PHP/Composer Docker wrappers in `others/env/bin` if they share real setup code. | Low | Run `php -v` and `composer --version` via the wrappers and confirm identical behavior. |
| 2.12 | Add shell validation for maintained files: `bash -n`, `zsh -n` where appropriate, `shellcheck` when available, and mocked dry-runs for commands that call system tools. | Medium | `scripts/check-dotfiles` reports startup-helper and tool-helper failures clearly. |

## Phase 3: Tool Package Boundaries and Selective Install

This phase makes selected tools installable without the whole dotfiles repo. It follows Phase 2 because the helper contract needs to exist before install/export logic can be correct.

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 3.1 | Create the dedicated `tools/` stow package for stable personal tools and shared helper layers. | Medium | `stow -n tools` or equivalent dry-run shows only intended `~/bin`, `~/.local/lib/dotfiles`, and shell helper links. |
| 3.2 | Define lightweight per-tool metadata listing executable files, helper dependencies, runtime commands, and profile tags. | Medium | `scripts/install-tool --dry-run wally` prints exactly which files and commands are required. |
| 3.3 | Add `scripts/install-tool <name>` for selective local installs into `~/.local/bin` and `~/.local/lib/dotfiles`, with `--dry-run` and `--prefix`. | Medium | Install only `wally` or only `rofi-vpn` into a temp prefix and confirm no unrelated dotfiles package is copied. |
| 3.4 | Keep full stow packages for normal dotfiles setup, but make tool packages usable without full stow. | Medium | `./stow.sh --packages tools --dry-run` and `scripts/install-tool --dry-run <name>` both describe valid, non-conflicting installs. |
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
| 5.4 | Make `desktop` include desktop config without host-specific extras. | Medium | Dry-run `--profile desktop`; confirm desktop packages are included without workstation-only hooks. |
| 5.5 | Make `workstation` the only profile that runs desktop hooks such as SDDM, Hyprland, fonts, wallpaper tooling, and optional local apps. | High | Dry-run `--profile workstation`; confirm hooks are listed but not run unless selected. |
| 5.6 | Add a `bootstrap-server.sh` one-liner for headless servers: `curl -sL <url> \| bash` clones repo shallowly and runs `./install.sh --profile server`. | Low | Test on a clean container to confirm zsh, git, nvim, and tmux are configured. |

## Phase 6: Shell and Server Portability

This phase applies the Phase 2 shell-helper model more broadly after immediate bugs are fixed and profiles exist. Keep interactive shell startup independent from desktop-only tools.

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 6.1 | Replace remaining duplicated PATH exports with the shared `path_prepend` and `path_append` helpers; use shell-native deduplication where appropriate. | Medium | Start a new zsh and bash shell where applicable; confirm no duplicate PATH entries or missing tool paths. |
| 6.2 | Remove host-specific `/Users/emon` and `/home/emon` paths from startup files; gate optional paths by directory existence. | Low | Run zsh on Linux and macOS-style path checks without errors. |
| 6.3 | Load NVM in one place only and make it optional. | Medium | Confirm shell startup works with and without `~/.nvm`. |
| 6.4 | Replace `zsh-setup.sh` repeated git clones with idempotent clone-or-update logic. | Medium | Run twice and confirm no failures if plugins already exist. |
| 6.5 | Stop starting a new `ssh-agent` on every shell startup; reuse an existing agent or make it opt-in. | Medium | Open multiple shells and confirm agent count does not grow. |
| 6.6 | Remove runtime `chmod -R` from `.zshrc`; store executable bits in git instead. | Low | Confirm aliases and sourced files still load. |
| 6.7 | Guard all `source` calls in startup files with shared `source_if_exists` or equivalent checks. | Medium | Start zsh with a missing optional file and confirm no errors. |
| 6.8 | Standardize shebangs to `#!/usr/bin/env bash` for maintained executable Bash scripts, with documented exceptions for curl-piped scripts. | Low | Run shell syntax checks on all maintained scripts after the change. |

## Phase 7: Split Desktop Packages by Ownership

Package splitting now happens after bugs, shared utilities, selective tool install, and profiles. That order is safer because files move only after their runtime contracts are clearer.

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 7.1 | Split `hyprland/.config/waybar` into a top-level `waybar/` stow package. | High | `stow -n hyprland waybar`; confirm target paths do not conflict. |
| 7.2 | Split `hyprland/.config/rofi` into top-level `rofi/`. | High | Test launcher paths and Hyprland keybinds after stowing. |
| 7.3 | Split `hyprland/.config/wallust` into top-level `wallust/`. | High | Run `wallust run <image>` and confirm all generated targets update. |
| 7.4 | Split notification config/templates into `dunst/` if current generated config is intended to be managed independently. | Medium | Confirm `dunst` starts and receives generated colors. |
| 7.5 | Move `wally` and other stable desktop helper commands into `tools` or `desktop-tools` according to the Phase 3 package boundary. | Medium | Confirm `~/bin/wally` exists after stow or selective install and `SUPER+W` still works. |

## Phase 8: Desktop Runtime Dependency Reduction

This phase completes desktop script decoupling after shared helpers exist. It should mostly apply the helper patterns from Phase 2.

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 8.1 | Add wallpaper backend adapter behavior to `wally`: prefer configured backend, support `swww`, `awww`, or no-op theme generation. | Medium | Test with installed backend and dry-run/no-op mode. |
| 8.2 | Require `rofi` only for picker mode, not direct `wally set <image>`. | Low | Run direct set on a minimal system without Rofi. |
| 8.3 | Require `realesrgan-ncnn-vulkan` only when `--upscale` is used. | Low | Run normal wallpaper set without the upscaler installed. |
| 8.4 | Wrap reloads for Waybar, Dunst, Kitty, Qt, GTK, OpenRGB, and Hyprland in `command -v` or process checks. | Medium | Run on a partial desktop and confirm missing tools do not abort the script. |
| 8.5 | Replace `go run ~/scripts/netspeed.go` in Waybar with a maintained script or compiled helper that does not spawn Go every interval. | Medium | Confirm Waybar shows speed and no Go process starts every interval. |
| 8.6 | Move inline Waybar command pipelines for memory/music into scripts under the appropriate package. | Low | Run each script directly and confirm expected output. |
| 8.7 | Gate optional Waybar modules behind package/profile choices. | Medium | Server/base profile should not require Waybar dependencies. |
| 8.8 | Review `startup/launch.sh` and start only commands that exist. | Medium | Start Hyprland with missing optional apps and confirm no noisy failures. |
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
| 10.6 | Keep shell syntax checks for all maintained Bash/Zsh scripts in the standard validation command. | Medium | Run checks locally and handle known third-party scripts separately. |

## Recommended Iteration Order

1. Phase 0 first, to establish a baseline before any changes.
2. Phase 1 next, because major bugs and destructive behavior must be fixed before refactors.
3. Phase 2 next, because shared utilities and script debloating should happen before moving scripts around.
4. Phase 3 next, because selective tool install depends on the helper contract from Phase 2.
5. Phase 4 next, because package-manager correctness affects install profiles.
6. Phase 5 next, so profiles define package and stow boundaries before desktop splits.
7. Phase 6 can proceed after profiles exist, with shell startup kept independent from desktop-only tools.
8. Phase 7 should be done in small commits: one stow package split at a time.
9. Phase 8 applies the shared-helper model to desktop runtime scripts and bars.
10. Phase 9 should be done carefully, especially if removing tracked large files or vendored Oh My Zsh.
11. Phase 10 happens continuously for touched areas, then gets a final pass at the end.

## First Concrete PR Scope

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| A | Fix `install_arch_with_pm` argument order. | High | Mock or dry-run package install path. |
| B | Replace stow conflict deletion with backups. | High | Test fake conflict under temp HOME. |
| C | Add `--dry-run` and package selection flags to `stow.sh`. | Medium | Confirm no filesystem changes occur in dry-run mode. |
| D | Fix `helpers.sh` invalid `local` at file scope. | Low | Start zsh, confirm no warnings. |
| E | Fix `.vimrc` dangling `if has("nvim")` block. | Low | Open vim, confirm no errors. |
| F | Fix `mac_setup.sh` nonexistent `source update.sh`. | Low | `bash -n mac_setup.sh` passes. |
| G | Fix `exports.sh` duplicates, typo, hardcoded NVM path, and duplicate NVM loading. | Low | New shell has clean PATH and NVM loads once. |
| H | Add internal dirs such as `.claude` to `.installignore`. | Low | Confirm stow dry-run skips them. |
| I | Add or update the first `scripts/check-dotfiles` safety command. | Medium | Command runs Phase 1 validations locally. |
| J | Document the new safety behavior. | Low | Confirm README/plan examples match commands. |

## Second Concrete PR Scope

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| A | Inventory maintained shell entrypoints, sourced files, and duplicated helper behavior. | Low | Produce the script/helper table. |
| B | Create the startup-safe shell helper layer. | Medium | Source helpers from zsh and bash with no load-time side effects. |
| C | Create the Bash tool helper layer. | Medium | Source helpers from Bash with no load-time side effects. |
| D | Apply path/source helpers to `exports.sh`, `.zshrc`, and sourced shell files. | Medium | New shell has clean PATH and missing optional files do not error. |
| E | Migrate `wally` and `rofi-vpn` as executable pilot scripts. | Medium | Both scripts run from repo checkout and temp install tree. |
| F | Add shell validation for maintained files. | Medium | `scripts/check-dotfiles` reports syntax/helper issues clearly. |
