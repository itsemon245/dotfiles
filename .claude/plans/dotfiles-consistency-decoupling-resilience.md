# Dotfiles Consistency, Decoupling, and Installer Resilience Plan

## Goals

- Make the installer resilient and non-destructive.
- Support Arch workstation installs as the primary path.
- Support Debian/Fedora server installs with only selected configs and tools.
- Reduce coupling between desktop components, package lists, and shell setup.
- Remove duplication and host-specific state from reusable configs.
- Keep changes incremental so each phase can be reviewed and rolled back.

## Risk Scale

- Low: Small, local, easy to validate, unlikely to break an installed system.
- Medium: Touches install flow, package selection, or interactive shell behavior.
- High: Can affect many symlinks, package installs, login/session startup, or user data.

## Phase 0: Baseline and Safety Checks

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 0.1 | Capture current `stow -n -v` output for every package and save as a baseline. | Low | Confirm output lists expected packages and known conflicts, especially `obsidian`. |
| 0.2 | Capture current package lists from `pocman/.config/pocman/*.toml`. | Low | Confirm no package list edits occur in this phase. |
| 0.3 | Add a `scripts/check-dotfiles` or `just check` command for shell syntax, stow dry-run, and basic path checks. | Low | Run the command locally and confirm failures are actionable. |
| 0.4 | Document known generated files and runtime artifacts before changing ignore rules. | Low | Compare against `.gitignore` and `git ls-files`. |

## Phase 1: Immediate Bug Fixes and Make Stow Non-Destructive

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 1.1 | Replace conflict deletion in `stow.sh` with timestamped backup to `~/.local/state/dotfiles/backups/<timestamp>/`. | High | Create a fake conflict in a temp HOME and confirm it is backed up, not deleted. |
| 1.2 | Add `--dry-run`, `--packages`, `--except`, and `--adopt` flags to `stow.sh`. | Medium | Run `./stow.sh --dry-run --packages zsh,tmux`; confirm only those packages are checked. |
| 1.3 | Stop hardcoding `cd ~/dotfiles`; resolve the repo root from the script path. | Medium | Run `stow.sh` from outside the repo and confirm package discovery still works. |
| 1.4 | Add `.claude` to `.installignore` so stow does not link internal dirs into `$HOME`. | Medium | Dry-run stow and confirm `.claude` is skipped. |
| 1.5 | Fix `zsh/zsh_utils/helpers.sh`: remove invalid `local` declarations at file scope (lines 2-7). | Low | Start a new zsh session and confirm no warnings from helpers.sh. |
| 1.6 | Fix `vim/.vimrc`: close the dangling `if has('nvim')` block at line 31 (missing `endif` before line 37). | Low | Open vim and confirm no syntax errors on startup. |
| 1.7 | Fix `mac_setup.sh` line 41: `source update.sh` references a nonexistent file — replace with `source stow.sh`. | Low | Run `bash -n mac_setup.sh` and confirm it parses without error. |
| 1.8 | Fix `exports.sh`: remove duplicate PATH `/opt/nvim-linux64/bin` (line 13, keep line 8), remove duplicate `QT_IM_MODULE=ibus` (line 22, keep line 7), fix typo `$/usr/local/bin` → `/usr/local/bin` (line 3). | Low | Start a new shell and confirm PATH is clean, no duplicate entries. |
| 1.9 | Remove hardcoded `$HOME/.nvm/versions/node/v20.11.1/bin` from exports.sh (line 21) — NVM already manages the active version's PATH. | Low | Confirm `node` still resolves after NVM loads. |
| 1.10 | Remove duplicate NVM loading — keep in `exports.sh` only (lines 17-19), remove from `.zshrc` (lines 19-21). | Low | Confirm NVM loads once, `nvm` command works. |

## Phase 2: Fix `pocman` Correctness and Reduce Mutation

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 2.1 | Fix `install_arch_with_pm` so it passes `create_type_file=false` before the package name. | High | Run a dry/isolated shell trace or mocked install call and confirm package args are preserved. |
| 2.2 | Batch install packages by package manager in `install_all_from_toml` instead of looping one package at a time. | Medium | Confirm `pacman`, `yay`, `paru`, `apt`, and `dnf` groups are parsed correctly. |
| 2.3 | Add `--dry-run` to `pocman` so it prints package groups without installing. | Medium | Run `pocman --all --only=cli --dry-run` on Arch and confirm no install command executes. |
| 2.4 | Stop mutating TOML files during `--all` installs; only mutate on explicit `pocman install <pkg>` operations. | Medium | Run `git diff` after `--all --dry-run` and after mocked install flows. |
| 2.5 | Split TOML parsing and package installation into smaller sourced files under `pocman/lib/`. | Medium | Run `bash -n` and current command examples after each extraction. |

## Phase 3: Add Install Profiles

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 3.1 | Create profile definitions: `base`, `server`, `desktop`, `workstation`, and optional `gaming`. | Medium | Print each profile and confirm intended packages/stow packages are included. |
| 3.2 | Change `install.sh` to accept `--profile`, `--only`, `--except`, `--dry-run`, and `--no-packages`. | High | Run dry-runs for Arch workstation and Debian/Fedora server paths. |
| 3.3 | Make `server` install only portable packages: shell, tmux, nvim, git, basic CLI tools, and selected scripts. | Medium | Dry-run on current machine with `--profile server`; confirm no Hyprland, SDDM, Waybar, Rofi, Qt, or gaming packages. |
| 3.4 | Make `workstation` the only profile that runs desktop hooks such as SDDM, Hyprland, fonts, and wallpaper tooling. | High | Dry-run `--profile workstation`; confirm hooks are listed but not run unless selected. |
| 3.5 | Add an explicit `--yes` flag for non-interactive installs. | Medium | Confirm unattended install exits if confirmation would be required and `--yes` is absent. |
| 3.6 | Add a `bootstrap-server.sh` one-liner for headless servers: `curl -sL <url> \| bash` clones repo (shallow) and runs `./install.sh --profile server`. | Low | Test on a clean container to confirm zsh+git+nvim+tmux are configured. |

## Phase 4: Split Desktop Packages by Ownership

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 4.1 | Split `hyprland/.config/waybar` into a top-level `waybar/` stow package. | High | `stow -n hyprland waybar`; confirm target paths do not conflict. |
| 4.2 | Split `hyprland/.config/rofi` into top-level `rofi/`. | High | Test launcher paths and Hyprland keybinds after stowing. |
| 4.3 | Split `hyprland/.config/wallust` into top-level `wallust/`. | High | Run `wallust run <image>` and confirm all generated targets update. |
| 4.4 | Split notification config/templates into `dunst/` if current generated config is intended to be managed independently. | Medium | Confirm `dunst` starts and receives generated colors. |
| 4.5 | Move `hyprland/bin/wally` into a dedicated `wally/` or `customization/bin/` package and update docs/keybinds. | Medium | Confirm `~/bin/wally` exists after stow and `SUPER+W` still works. |

## Phase 5: Clean Shell and Server Portability

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 5.1 | Replace duplicated PATH exports with `path_prepend` and `path_append` helpers; use `typeset -U path` for deduplication. | Medium | Start a new zsh and confirm no duplicate PATH entries or missing tool paths. |
| 5.2 | Remove host-specific `/Users/emon` and `/home/emon` paths from `.zshrc`; gate optional paths by directory existence. | Low | Run zsh on Linux and macOS-style path checks without errors. |
| 5.3 | Load NVM in one place only and make it optional. | Medium | Confirm shell startup works with and without `~/.nvm`. |
| 5.4 | Replace `zsh-setup.sh` repeated git clones with idempotent clone-or-update logic. | Medium | Run twice and confirm no failures if plugins already exist. |
| 5.5 | Stop starting a new `ssh-agent` on every shell startup; reuse an existing agent or make it opt-in. | Medium | Open multiple shells and confirm agent count does not grow. |
| 5.6 | Remove runtime `chmod -R` from `.zshrc`; store executable bits in git instead. | Low | Confirm aliases and sourced files still load. |
| 5.7 | Guard all `source` calls in `.zshrc` with existence checks (`[[ -f ... ]] && source ...`). | Medium | Start zsh with a missing plugin dir and confirm no errors. |
| 5.8 | DRY the PHP/Composer Docker wrappers in `others/env/bin/` — extract shared Docker setup into `_docker-php-common.sh`. | Low | Run `php -v` and `composer --version` via the wrappers and confirm identical behavior. |
| 5.9 | Standardize shebangs to `#!/usr/bin/env bash` for portability (exception: curl-piped scripts keep `#!/bin/bash`). | Low | Run `shellcheck` or `bash -n` on all scripts after the change. |

## Phase 6: Decouple `wally` and Desktop Runtime Hooks

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 6.1 | Add optional notification adapter: use `dunstify` when present, else print to stdout. | Low | Run `wally set image --no-upscale` without Dunst available. |
| 6.2 | Add wallpaper backend adapter: prefer configured backend, support `swww`, `awww`, or no-op theme generation. | Medium | Test with installed backend and dry-run/no-op mode. |
| 6.3 | Require `rofi` only for picker mode, not direct `wally set <image>`. | Low | Run direct set on a minimal system without Rofi. |
| 6.4 | Require `realesrgan-ncnn-vulkan` only when `--upscale` is used. | Low | Run normal wallpaper set without the upscaler installed. |
| 6.5 | Stop deleting original wallpapers during PNG normalization; write normalized files into cache. | Medium | Convert JPG/WEBP and confirm source file remains. |
| 6.6 | Wrap reloads for Waybar, Dunst, Kitty, Qt, GTK, OpenRGB, and Hyprland in `command -v` or process checks. | Medium | Run on a partial desktop and confirm missing tools do not abort the script. |

## Phase 7: Reduce Runtime Dependencies in Bars and Scripts

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 7.1 | Replace `go run ~/scripts/netspeed.go` in Waybar with a small shell script reading `/sys/class/net`. | Medium | Confirm Waybar shows speed and no Go process starts every interval. |
| 7.2 | Move inline Waybar command pipelines for memory/music into scripts under `waybar/scripts/`. | Low | Run each script directly and confirm expected output. |
| 7.3 | Gate optional Waybar modules behind package/profile choices. | Medium | Server/base profile should not require Waybar dependencies. |
| 7.4 | Review `startup/launch.sh` and start only commands that exist. | Medium | Start Hyprland with missing optional apps and confirm no noisy failures. |
| 7.5 | Move Slack/LocalSend autostart to a host/workstation-specific hook. | Low | Confirm workstation profile can enable them, desktop profile can skip them. |

## Phase 8: Repository Hygiene and Generated Artifacts

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 8.1 | Remove or ignore tracked runtime artifacts: qBittorrent state, backups, shell history, OpenRGB logs, and local `.env` files. | Medium | Confirm examples remain, secrets/state are untracked, and app configs still have templates. |
| 8.2 | Remove the large game archive from the repo and add archive patterns to `.gitignore`. | Medium | Confirm repository size decreases after history cleanup if that is chosen. |
| 8.3 | Replace vendored `zsh/.oh-my-zsh` with bootstrap-managed install or git submodules. | High | Fresh install must still produce a working Zsh setup; offline expectations should be documented. |
| 8.4 | Decide whether fonts are repo assets or package-managed dependencies; avoid doing both for the same font family. | Medium | Confirm fontconfig and Waybar/Kitty font names resolve after install. |
| 8.5 | Ensure generated Wallust outputs are ignored consistently and only templates are tracked. | Low | Run `wallust run` and confirm generated color files do not appear in `git status`. |
| 8.6 | Remove nested `.git` directories from vendored zsh plugins (`zsh-autosuggestions/.git`, `zsh-syntax-highlighting/.git`). | Low | Confirm plugins still load correctly without their `.git` dirs. |
| 8.7 | Consider replacing oh-my-zsh entirely with direct plugin loading (~10 lines vs 15MB framework). | High | Full `.zshrc` rewrite; only attempt after all other shell changes are stable. Requires custom PROMPT or starship. |

## Phase 9: Validation and Documentation

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| 9.1 | Update `README.md` and `AGENTS.md` to match actual package layout after splitting. | Low | Read install examples and confirm paths exist. |
| 9.2 | Add a quickstart for Arch workstation, Debian server, and Fedora server. | Low | Copy commands into shell with `--dry-run` and confirm they parse. |
| 9.3 | Add recovery docs for stow conflicts and backup restore. | Low | Confirm backup path and restore command examples match implementation. |
| 9.4 | Add a smoke-test checklist for a new machine. | Low | Run checklist on current machine after refactor. |
| 9.5 | Add shell syntax checks for all maintained Bash/Zsh scripts. | Medium | Run checks in CI/local command and handle known third-party scripts separately. |

## Recommended Iteration Order

1. Phase 0 first, to establish a baseline before any changes.
2. Phase 1 next, because non-destructive stow and bug fixes protect user data and establish correctness.
3. Phase 2 next, because package installation correctness affects every later phase.
4. Phase 3 before package splitting, so profiles define the desired boundaries.
5. Phase 4 in small commits: one stow package split at a time.
6. Phase 5 and Phase 6 can proceed independently after profiles exist.
7. Phase 8 should be done carefully, especially if removing tracked large files or vendored Oh My Zsh.

## First Concrete PR Scope

| Step | Change | Risk | Validation |
| --- | --- | --- | --- |
| A | Fix `install_arch_with_pm` argument order. | High | Mock or dry-run package install path. |
| B | Fix `helpers.sh` invalid `local` at file scope. | Low | Start zsh, confirm no warnings. |
| C | Fix `.vimrc` dangling `if has('nvim')` block. | Low | Open vim, confirm no errors. |
| D | Fix `mac_setup.sh` nonexistent `source update.sh`. | Low | `bash -n mac_setup.sh` passes. |
| E | Fix `exports.sh` duplicates and typo. | Low | New shell has clean PATH. |
| F | Add `--dry-run` to `stow.sh`. | Medium | Confirm no filesystem changes occur. |
| G | Replace stow conflict deletion with backups. | High | Test fake conflict under temp HOME. |
| H | Add `.claude` to `.installignore`. | Low | Confirm stow dry-run skips it. |
| I | Document the new safety behavior. | Low | Confirm README/plan examples match commands. |
