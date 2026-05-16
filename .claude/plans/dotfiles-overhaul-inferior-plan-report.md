# Inferior Plan Flaws Report

## Verdict

Inferior plan: `.claude/plans/dotfiles-overhaul.md`

Stronger plan: `.claude/plans/dotfiles-consistency-decoupling-resilience.md`

The consistency/decoupling/resilience plan is objectively better for this repository because it is more accurate to the current tree, starts with safety and validation, identifies a real `pocman --all` correctness bug, and covers runtime coupling in `wally`, Waybar, Hyprland startup, and shell startup that the overhaul plan misses.

## Why The Overhaul Plan Is Weaker

### 1. It does not prioritize the most dangerous existing behavior

The current `stow.sh` deletes conflicting home files and directories with `rm -rf` / `rm -f` before stowing:

- `stow.sh:83-87`

The current `install.sh` also deletes user state:

- `install.sh:37` removes `~/.config/pocman`
- `install.sh:47` removes `~/.zshrc`

The overhaul plan mentions backups, but only after "quick fixes" and helper-library work. The better plan makes non-destructive stow the first real implementation phase and adds explicit validation around fake conflicts and dry runs.

### 2. Its `.claude` recommendation is wrong for this repo

The overhaul plan says to add `claude/` to `.gitignore` and claims the directory is already removed:

- `.claude/plans/dotfiles-overhaul.md:28-29`

The actual repo has `.claude/`, `.agents/`, and `.codex/` at the top level, and `.installignore` only excludes:

- `.gitignore`
- `.git`
- `user`
- `system`
- `sddm`

That means `stow.sh` can currently treat internal hidden directories as stow packages. The better plan correctly targets `.installignore` and names `.agents`, `.claude`, and `.codex`.

### 3. It misses a real `pocman --all` correctness bug

The current compatibility helper is broken:

- `install_arch_with_pm()` calls `install_arch_batch "$package_manager" "" "$package"` at `pocman/bin/pocman:913-917`.
- `install_arch_batch()` expects `package_manager`, `explicit_type`, `create_type_file`, then package names.

So the package name is consumed as `create_type_file`, leaving no package arguments. In the `--all` path, `install_all_from_toml()` loops package-by-package and calls that broken helper at `pocman/bin/pocman:1516-1548`.

The overhaul plan explicitly says "`pocman` stays as-is" and "already handles cross-distro well":

- `.claude/plans/dotfiles-overhaul.md:179`

That is materially incorrect given the current code. The better plan identifies the exact argument-order fix as its first concrete PR item.

### 4. It relies on `pocman --all --only=cli` without first making it safe or observable

The overhaul plan proposes profile integration with:

- `pocman --all --only=cli`
- `pocman --all`

But there is no current `--dry-run` support in `pocman` argument parsing, and `--all` has the bug above. The better plan adds `--dry-run`, stops mutation during bulk installs, and validates parsed package groups before relying on profiles.

### 5. It has weaker validation discipline

The overhaul plan has no baseline phase. It moves directly into edits.

The better plan starts by capturing:

- current `stow -n -v` output
- current package lists
- known generated files and runtime artifacts
- a future `scripts/check-dotfiles` or `just check`

That matters in this repo because many planned changes affect symlinks, home-directory files, package installs, and session startup.

### 6. It misses important shell startup portability issues

The overhaul plan catches `zsh/exports.sh` duplication and NVM duplication, which is useful. But it misses several actual shell startup problems:

- host-specific `/Users/emon` paths in `zsh/.zshrc:25` and `zsh/.zshrc:30`
- host-specific `/home/emon` path in `zsh/.zshrc:33`
- runtime `chmod -R` on every shell startup in `zsh/.zshrc:10-12`
- unconditional new ssh-agent per shell in `zsh/ssh-agent.sh:1`

The better plan names all of these in its shell cleanup phase.

### 7. It does not address `wally`'s direct-mode coupling and data-loss risk

The current `wally` script requires every dependency even for direct `wally set <image>` usage:

- dependency list: `hyprland/bin/wally:37-38`
- missing dependency exits: `hyprland/bin/wally:196-205`

It also deletes the original JPG/WEBP source during PNG normalization:

- `hyprland/bin/wally:258-264`

And it reloads desktop services without command/process guards:

- `hyprland/bin/wally:87-108`

The overhaul plan talks about moving/splitting modules, but it does not address these behavior-level risks. The better plan does.

### 8. It misses Waybar and Hyprland runtime dependency problems

The current Waybar config runs Go every second for network speed:

- `hyprland/.config/waybar/modules.jsonc:91-94`

The current Hyprland startup script launches optional workstation apps without guards:

- `hyprland/.config/hypr/startup/launch.sh:30-34`

The better plan includes both issues. The overhaul plan does not, even though they directly affect desktop resilience and profile portability.

### 9. It includes a false task about nested zsh plugin git directories

The overhaul plan says to remove vendored plugin `.git` dirs:

- `.claude/plans/dotfiles-overhaul.md:144-146`

But scanning `zsh` for nested `.git` directories found none. This is at best stale and at worst a misleading task.

### 10. Its Wallust-generated-file decision conflicts with current ignore policy

The overhaul plan decision log says Wallust-generated files should stay in the repo:

- `.claude/plans/dotfiles-overhaul.md:180`

The current `.gitignore` already ignores generated Wallust outputs:

- `hyprland/.config/hypr/colors.conf`
- `hyprland/.config/rofi/colors/wallust.rasi`
- `hyprland/.config/waybar/colors.css`
- GTK color CSS files
- `tmux/.tmux-colors.conf`
- `kitty/.config/kitty/colors.conf`

The better plan's "only templates are tracked" direction matches the current ignore policy better.

### 11. Its profile model is less precise for this repo

The overhaul plan uses broad tiers: core, cli, desktop, full, mac. That is workable, but less precise than the better plan's `base`, `server`, `desktop`, `workstation`, and optional `gaming` model.

This repo has a strong distinction between:

- portable server configs
- desktop configs
- workstation-only hooks like SDDM, Hyprland startup apps, wallpaper tooling, fonts, OpenRGB, and gaming packages

The better plan also adds `--dry-run`, `--no-packages`, and `--yes`, which are important for safe bootstrapping.

### 12. It underestimates repository hygiene work

The overhaul plan mainly focuses on Oh My Zsh vendoring. That is real: `zsh/.oh-my-zsh` is about 15 MB and has 1011 tracked files.

But the repo also has hygiene issues the better plan catches:

- tracked qBittorrent state and backup files under `others/downloader/qb_config`
- tracked shell history at `others/downloader/qb_config/.ash_history`
- a tracked game archive at the repo root
- generated/runtime artifacts that need consistent policy

The better plan is more complete for reducing repo state that should not be shared across machines.

## Useful Parts Of The Overhaul Plan

The overhaul plan is not useless. Its best parts are:

- it correctly identifies `zsh/exports.sh` duplication and the bad `$/usr/local/bin` PATH entry
- it correctly identifies destructive installer actions in `install.sh`
- it correctly sees that `hyprland/` is currently a mega-package that should be split
- it correctly flags Oh My Zsh vendoring as a repo-size issue

The problem is sequencing and coverage. It spends early attention on small cleanup while missing or deferring higher-risk correctness and data-safety issues that are present in the current repository.

## Recommended Path

Use `.claude/plans/dotfiles-consistency-decoupling-resilience.md` as the base plan.

Fold in only these items from the overhaul plan:

- the exact `zsh/exports.sh` cleanup list
- the note that SDDM theme installation may need copy semantics rather than stow symlinks
- the Oh My Zsh repo-size observation, with a clear offline-install decision

Do not use the overhaul plan as the primary roadmap without first fixing the `pocman` omission, `.claude`/`.installignore` mistake, safety sequencing, and missing runtime-coupling work.
