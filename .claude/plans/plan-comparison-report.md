# Plan Comparison Report: Independent Analysis

## Verdict

**Winner:** `dotfiles-consistency-decoupling-resilience.md`

**Inferior:** `dotfiles-overhaul.md`

---

## Methodology

I scanned the actual codebase and verified each plan's claims against what exists in the repository today. Below are the specific flaws I found in the overhaul plan, backed by file evidence.

---

## Flaws in `dotfiles-overhaul.md`

### Flaw 1: Factually incorrect claim about `pocman`

**Overhaul plan states (line 179):** "pocman stays as-is" / "Already handles cross-distro well"

**Reality:** `install_arch_with_pm()` at `pocman/bin/pocman:913-917` is broken:

```bash
install_arch_with_pm() {
    local package=$1
    local package_manager=$2
    install_arch_batch "$package_manager" "" "$package"
}
```

But `install_arch_batch()` at line 846 expects:
```bash
install_arch_batch() {
    local package_manager=$1
    local explicit_type=$2
    local create_type_file=$3  # <-- "$package" lands here
    shift 3
    local packages=("$@")      # <-- empty!
}
```

The package name is consumed as `create_type_file`, leaving zero packages to install. The `--all` code path at lines 1516-1548 calls `install_arch_with_pm` in a loop, so **bulk installs are silently broken**.

The consistency plan identifies this bug and makes it the first PR item. The overhaul plan declares the tool working and builds profiles on top of it.

### Flaw 2: Wrong `.claude` recommendation

**Overhaul plan states (line 28-29):** "Add `claude/` to `.gitignore`" / "directory already removed"

**Reality:** `.claude/`, `.agents/`, and `.codex/` all exist as top-level directories. The `.installignore` file only excludes: `.gitignore`, `.git`, `user`, `system`, `sddm`.

This means `stow.sh` currently discovers `.claude`, `.agents`, and `.codex` via its `find . -maxdepth 1 -mindepth 1 -type d` command (line 42) and could attempt to stow them into `$HOME`. Adding them to `.gitignore` does nothing — they need to be in `.installignore`.

The consistency plan correctly identifies this at Phase 1, Step 1.4.

### Flaw 3: Wrong sequencing — cleanup before safety

The overhaul plan starts with "Quick Fixes" (export deduplication, sleep removal, `set -euo pipefail`) and defers safety to Phase 2.

But the most dangerous current behavior is `stow.sh` lines 83-87:
```bash
if [ -d "$target_path" ]; then
    rm -rf "$target_path" 2>/dev/null
else
    rm -f "$target_path" 2>/dev/null
fi
```

And `install.sh`:
- Line 37: `rm -rf ~/.config/pocman`
- Line 47: `rm -f ~/.zshrc`

These destroy user data on every run. The consistency plan makes fixing this Phase 1 with backups, dry-run flags, and validation. That's the correct priority.

### Flaw 4: Builds profiles on broken foundations

The overhaul plan (Phase 5.3) proposes:
- `pocman --all --only=cli` for core/cli tier
- `pocman --all` for desktop tier

Neither `--dry-run` exists in pocman, nor does the `--all` path work correctly (Flaw 1). The consistency plan adds `--dry-run` to pocman (Phase 2.3), fixes the bug (Phase 2.1), and validates parsed package groups before defining profiles.

### Flaw 5: No baseline/validation phase

The overhaul plan goes straight into code edits. The consistency plan captures:
- Current `stow -n -v` output for every package
- Current package lists from TOML files
- Known generated files vs runtime artifacts
- A `scripts/check-dotfiles` or `just check` command

This is important because changes to stow packages, symlinks, and package installs interact in ways that are hard to debug after the fact.

### Flaw 6: Misses shell startup problems

The overhaul plan correctly catches `exports.sh` duplication (good). But it misses:

| Issue | Location | Impact |
|-------|----------|--------|
| `chmod -R +x` on every shell startup | `zsh/.zshrc:10-12` | Unnecessary filesystem mutation each time a shell opens |
| New ssh-agent per shell | `zsh/ssh-agent.sh:1` (`eval "$(ssh-agent -s)"`) | Agent processes accumulate with each terminal |
| macOS-specific `/Users/emon` paths | `zsh/.zshrc:25,30` | Broken references on Linux |
| Host-specific `/home/emon` paths | `zsh/.zshrc:33` | Not portable to other usernames |

The consistency plan addresses all of these in Phase 5.

### Flaw 7: Misses `wally` data-loss and coupling issues

The overhaul plan talks about splitting `hyprland/` into modules but doesn't address the actual behavior problems:

1. **Data loss:** `hyprland/bin/wally:264` — `rm "$FULL_PATH"` deletes the original image after converting to PNG
2. **Hard dependency wall:** Line 38 requires `rofi`, `awww`, `identify`, `convert`, `realesrgan-ncnn-vulkan`, `dunstify`, and `wallust` even for `wally set <image>` (lines 196-205 exit on any missing dep)
3. **Unguarded reloads:** Lines 90-92 (`pkill waybar`, `killall dunst`, `killall -SIGUSR1 kitty`) have no `command -v` guards — they fail noisily on partial desktop setups

The consistency plan dedicates Phase 6 to all of these.

### Flaw 8: Misses Waybar `go run` performance issue

`hyprland/.config/waybar/modules.jsonc:93`:
```json
"exec": "go run ~/scripts/netspeed.go",
"interval": 1
```

This compiles and runs a Go program every second. The consistency plan proposes replacing it with a shell script reading `/sys/class/net`. The overhaul plan doesn't mention it.

### Flaw 9: Misses unguarded startup apps

`hyprland/.config/hypr/startup/launch.sh:31-34`:
```bash
slack -u
localsend --hidden
```

No `command -v` guard. If Slack or LocalSend aren't installed (e.g., on a fresh desktop-only install without workstation apps), these fail. The consistency plan addresses this in Phase 7.5.

### Flaw 10: Wallust decision contradicts existing `.gitignore`

**Overhaul plan decision log (line 180):** "Wallust-generated files stay in repo"

**Actual `.gitignore` already ignores them:**
- `hyprland/.config/hypr/colors.conf`
- `hyprland/.config/rofi/colors/wallust.rasi`
- `hyprland/.config/waybar/colors.css`
- `customization/.config/gtk-4.0/colors.css`
- `customization/.config/gtk-3.0/colors.css`
- `tmux/.tmux-colors.conf`
- `kitty/.config/kitty/colors.conf`

The consistency plan's "only templates are tracked" approach matches what the repo already does.

### Flaw 11: Less precise profile model

Overhaul tiers: `core`, `cli`, `desktop`, `full`, `mac`

Consistency profiles: `base`, `server`, `desktop`, `workstation`, `gaming` (optional)

The repo has clear boundaries between:
- Server-portable configs (shell, git, nvim, tmux)
- Desktop configs (Hyprland, Waybar, Rofi, Kitty)
- Workstation-only things (SDDM, fonts, OpenRGB, Slack, LocalSend, gaming)

The consistency plan's model maps more precisely to these boundaries and adds `--dry-run`, `--no-packages`, `--yes` flags for safe bootstrapping.

### Flaw 12: Ignores repo hygiene beyond Oh My Zsh

The overhaul plan mentions Oh My Zsh vendoring (15MB, 1466 files — confirmed). But it misses:

- Tracked qBittorrent state: torrent files, fastresume, GeoDB, logs, `.ash_history`, `.env` file in `others/downloader/`
- A 4KB game archive placeholder at repo root: `Little Nightmares - Complete Edition [FitGirl Repack].tar.zst`
- No archive patterns in `.gitignore`
- qBittorrent backup config (`qBittorrent.conf.bak.20260220174419`)

The consistency plan covers all of these in Phase 8.

---

## What The Overhaul Plan Gets Right

It's not without merit:

- Correctly identifies all `exports.sh` bugs (typo `$/usr/local/bin`, duplicates, hardcoded node path)
- Correctly identifies NVM double-loading
- Correctly sees `hyprland/` needs splitting
- Correctly notes SDDM needs `sudo cp` not symlinks
- Correctly identifies Oh My Zsh repo bloat
- Correctly identifies nested `.git` dirs in vendored plugins (confirmed: `zsh-autosuggestions/.git`, `zsh-syntax-highlighting/.git` exist)
- The `bootstrap-server.sh` curl one-liner idea is nice for UX

---

## Summary Table

| Dimension | Overhaul | Consistency |
|-----------|----------|-------------|
| Identifies real bugs | Misses pocman bug | Catches it, makes it PR #1 |
| Safety-first | Defers to Phase 2 | Phase 1 |
| Validation/baseline | None | Phase 0 |
| Shell issues found | 3 (exports only) | 7+ (exports, chmod, ssh-agent, paths) |
| Runtime coupling | Not addressed | Phases 6-7 |
| Data loss risks | Not addressed | wally normalization, stow conflicts |
| Factual accuracy | 2 wrong claims | Verified against code |
| Profile precision | Broad tiers | Matches actual repo boundaries |
| Repo hygiene | Oh My Zsh only | Comprehensive |

---

## Recommendation

Use `dotfiles-consistency-decoupling-resilience.md` as your roadmap. Cherry-pick from the overhaul plan:
- The specific `exports.sh` line-by-line cleanup list
- The SDDM copy-semantics note
- The `bootstrap-server.sh` curl one-liner idea
- The nested `.git` directory observation
