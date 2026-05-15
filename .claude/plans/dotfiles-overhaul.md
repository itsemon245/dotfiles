# Dotfiles Overhaul Plan

Goal: Improve consistency, reduce duplication, decouple modules, harden installer, enable cross-distro server bootstrapping.

Risk levels: `SAFE` = no functional change, `LOW` = equivalent behavior, `MEDIUM` = could break edge cases, `HIGH` = breaking change requiring testing.

---

## Phase 1: Quick Fixes (no structural changes)

### 1.1 Fix `zsh/exports.sh` bugs and duplication
- [ ] `SAFE` Remove duplicate `export PATH="$PATH:/opt/nvim-linux64/bin"` (line 13, keep line 8) — exact duplicate line
- [ ] `SAFE` Remove duplicate `export QT_IM_MODULE=ibus` (line 22, keep line 7) — exact duplicate line
- [ ] `SAFE` Fix typo `$/usr/local/bin` -> `/usr/local/bin` (line 3) — currently broken anyway
- [ ] `LOW` Remove hardcoded node path `$HOME/.nvm/versions/node/v20.11.1/bin` (line 21) — NVM already adds the active version to PATH; this line only works for one specific version
- [ ] `LOW` Consolidate 12 separate `export PATH=` lines into a single `typeset -U path` array — functionally identical, `typeset -U` is zsh-native and auto-deduplicates
- [ ] `LOW` Remove NVM loading from exports.sh (keep in .zshrc, lines 19-21) — .zshrc sources exports.sh first then loads NVM itself; removing from exports.sh means NVM loads once instead of twice

### 1.2 Add `set -euo pipefail` to all installer scripts
- [ ] `HIGH` `install.sh` — uses `source` chaining; if any sourced script fails mid-way, the whole thing aborts. `stow.sh` uses `grep` and `stow -n` which return non-zero on no-match. `command -v` returns 1 when command missing. Every script needs auditing for legitimate non-zero exits before adding this. **Defer to Phase 2** where each script is hardened individually.
- [ ] `HIGH` `stow.sh` — `stow -n` returns non-zero on conflicts (intentional), `grep -v` returns 1 on no match, `find` piped through grep
- [ ] `MEDIUM` `zsh-setup.sh` — `git clone` fails if dir exists, `chsh` fails if zsh not installed
- [ ] `LOW` `nvm-setup.sh` — single curl|bash command, `set -e` would catch download failures
- [ ] `MEDIUM` `mac_setup.sh` — sources other scripts; same chaining risk as install.sh
- [ ] `MEDIUM` `mac_install_packages.sh` — `brew list` returns non-zero if package not found (used intentionally in the check)
- [ ] `LOW` `sddm/update.sh` — single `sudo cp -r` command, `set -e` would catch permission failures

### 1.3 Add `claude/` to `.gitignore`
- [ ] `SAFE` Preventive — directory already removed, just stops accidental future commits

### 1.4 Remove unnecessary `sleep 0.1` in `stow.sh`
- [ ] `SAFE` Cosmetic only — removes ~2 seconds of artificial delay across ~18 packages

---

## Phase 2: Installer Resilience

### 2.1 Create `lib/helpers.sh` — shared functions for all scripts
- [ ] `LOW` `detect_distro()` — returns arch|debian|fedora|macos|unknown. New code, no existing behavior changed.
- [ ] `LOW` `has_display()` — returns true|false (checks DISPLAY/WAYLAND_DISPLAY). New code.
- [ ] `LOW` `ensure_cmd()` — install a command if missing, using detected package manager. New code.
- [ ] `LOW` `backup_file()` — mv existing file to `*.bak.<timestamp>` before overwriting. New code.
- [ ] `LOW` `stow_pkg()` — stow a single package with conflict handling. New code, replaces stow.sh logic later.
- [ ] `LOW` `log_info()`, `log_warn()`, `log_error()` — replace raw `echo -e` color calls. New code.
- [ ] `LOW` Absorb `colors.sh` into `lib/helpers.sh` — other scripts that `source colors.sh` must be updated to `source lib/helpers.sh`. Low risk if done atomically.

### 2.2 Harden `install.sh`
- [ ] `MEDIUM` Use `set -euo pipefail` — safe only after all called scripts are audited (2.3-2.5)
- [ ] `SAFE` Resolve `DOTFILES_DIR` with `$(cd "$(dirname "$0")" && pwd)` — fixes the relative path bug when run from another directory
- [ ] `LOW` Backup `~/.zshrc` before removing — adds safety, no downside
- [ ] `LOW` Don't `rm -rf ~/.config/pocman` — currently destroys custom pocman config; stow should handle conflicts instead
- [ ] `LOW` Add idempotency: skip steps already done (git clone, chsh, plugin clones) — guard with `[ -d ... ]` checks

### 2.3 Harden `zsh-setup.sh`
- [ ] `LOW` Check if zsh is installed before `chsh` — currently fails with confusing error if zsh missing
- [ ] `LOW` Skip `git clone` if plugin dirs already exist — currently fails on second run
- [ ] `LOW` Handle case where oh-my-zsh isn't installed yet — add clone/install step

### 2.4 Harden `stow.sh`
- [ ] `MEDIUM` Use `backup_file` instead of `rm -rf` for conflict resolution — safer but creates `.bak` files user must clean up
- [ ] `LOW` Guard against blank lines in `.installignore` matching everything — add `grep -v '^$'` to filter
- [ ] `SAFE` Remove `sleep 0.1` — same as 1.4

### 2.5 Harden `sddm/update.sh`
- [ ] `LOW` Check if sddm is installed before copying — `command -v sddm` guard
- [ ] `LOW` Add error handling around `sudo cp -r` — report failure clearly
- [ ] Note: `sudo cp -r` is intentional — SDDM does not support symlinks for themes

---

## Phase 3: Modular Architecture (tier-based install)

### 3.1 Define module tiers

**Tier 0 — Core** (works on any Linux/macOS, no GUI needed):
- `zsh/` — shell config
- `git/` — git config (split from `others/`)
- `nvim/` — editor config
- `tmux/` — terminal multiplexer
- `vim/` — fallback editor

**Tier 1 — CLI tools** (still no GUI):
- `fastfetch/`
- `pocman/`
- `composer/`

**Tier 2 — Desktop** (Arch workstation):
- `hyprland/`
- `rofi/` (split from hyprland)
- `waybar/` (split from hyprland)
- `wallust/` (split from hyprland)
- `kitty/`
- `customization/`
- `systemd/`
- `sddm/`
- `fonts/`
- `omarchy/`

**Tier 3 — Platform-specific**:
- `mac-wm/`
- `obsidian/`

### 3.2 Rewrite `install.sh` with tier support
- [ ] `MEDIUM` `./install.sh` — auto-detect (GUI -> desktop, headless -> core). Risk: auto-detection could misidentify environment (e.g. SSH into GUI machine has no DISPLAY).
- [ ] `SAFE` `./install.sh core` — only tier 0. Explicit, no guessing.
- [ ] `SAFE` `./install.sh cli` — tier 0 + tier 1. Explicit.
- [ ] `SAFE` `./install.sh desktop` — tier 0 + 1 + 2. Explicit.
- [ ] `SAFE` `./install.sh full` — everything. Explicit.
- [ ] `LOW` `./install.sh mac` — macOS path (tier 0 + 1 + mac-wm). Replaces mac_setup.sh.

### 3.3 Create `bootstrap-server.sh`
- [ ] `SAFE` New file, doesn't touch existing behavior
One-liner for servers:
```
curl -sL https://itsemon245.github.io/dotfiles/bootstrap-server.sh | bash
```
- Clones repo (shallow), runs `./install.sh core`
- Gets you zsh + git + nvim + tmux on any debian/fedora/arch server

### 3.4 Update `.installignore` per tier
- [ ] `MEDIUM` Replace single `.installignore` with tier-based stow lists — changes how stow.sh decides what to install. Must ensure backward compat if someone runs `stow.sh` directly.

---

## Phase 4: Decouple Modules

### 4.1 Split `others/` into focused packages
- [ ] `MEDIUM` `git/` — just `.config/git/config`. Must unstow `others/` first, then restow new packages. Symlinks will break momentarily.
- [ ] `MEDIUM` `docker-dev/` — the `env/` directory (docker-compose, Dockerfile, bin/php, bin/composer). Same unstow/restow dance.
- [ ] `LOW` Keep ngrok, containers/policy.json, qBittorrent in `others/` or further split

### 4.2 Split `hyprland/` mega-module
- [ ] `MEDIUM` `hyprland/` — only `.config/hypr/` (hyprland.conf + partials). Must unstow hyprland, move files, restow. All symlinks break during transition.
- [ ] `MEDIUM` `rofi/` — `.config/rofi/` (100+ files, works with any WM). Same transition risk.
- [ ] `MEDIUM` `waybar/` — `.config/waybar/`. Same.
- [ ] `MEDIUM` `wallust/` — `.config/wallust/` (templates generate colors for kitty, tmux, hyprland, sddm). Same. Also: wallust regenerates files in-place, must verify it still finds templates after move.

### 4.3 Stop vendoring oh-my-zsh
- [ ] `MEDIUM` Add `zsh/.oh-my-zsh/` to `.gitignore` — repo shrinks ~15MB. Risk: existing installs that relied on the vendored copy now need internet to install oh-my-zsh.
- [ ] `LOW` Install oh-my-zsh at setup time (in `zsh-setup.sh`) — standard approach, well-documented upstream installer
- [ ] `HIGH` Or switch to lighter plugin manager (zinit, antidote) — full .zshrc rewrite, different plugin syntax, changes shell startup behavior significantly
- [ ] `LOW` This saves ~15MB from the repo

### 4.4 Remove vendored zsh plugin `.git` dirs
- [ ] `SAFE` If keeping vendored plugins: delete `zsh-autosuggestions/.git` and `zsh-syntax-highlighting/.git` — these nested .git dirs serve no purpose in the main repo
- [ ] `LOW` If cloning at install time: just `.gitignore` them

---

## Phase 5: Polish

### 5.1 Consolidate color/defaults
- [ ] `LOW` Create a central `defaults.env` sourced by hyprland, git, zsh aliases:
  ```
  TERMINAL=kitty
  BROWSER=google-chrome-stable
  EDITOR=nvim
  MENU=rofi
  ```
  Risk: each consumer must be updated to read from this file. If file is missing, configs break. Need fallback values.

### 5.2 Update README
- [ ] `SAFE` Document tier system
- [ ] `SAFE` Document server bootstrap one-liner
- [ ] `SAFE` List what each module provides

### 5.3 Integrate pocman with tier system
- [ ] `LOW` `pocman --all --only=cli` for core/cli tier — pocman already supports this flag
- [ ] `LOW` `pocman --all` for desktop tier — existing behavior
- [ ] `SAFE` Document that pocman already handles cross-distro, so install.sh just delegates to it

---

## Decision Log

| Decision | Reason |
|----------|--------|
| SDDM uses `sudo cp -r`, not stow symlinks | SDDM doesn't load themes from symlinks |
| pocman stays as-is | Already handles cross-distro well, 2K+ lines of working code |
| Wallust-generated files stay in repo | Useful as defaults even without wallust installed |
| `set -euo pipefail` deferred to Phase 2 | Too many scripts use non-zero exits intentionally; needs per-script audit |
