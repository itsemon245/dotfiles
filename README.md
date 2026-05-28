## Getting Started

### One Liner installation
```sh
sh <(curl -sL https://itsemon245.github.io/dotfiles/install.sh)
```

### Safe stow

`stow.sh` is non-destructive by default. When an existing target conflicts
with a dotfile, it prompts before changing anything:

- `Y` or `y`: back up this conflict only.
- `N` or `n`: skip this package.
- `D` or `d`: delete this conflict and all later conflicts for this run.
- `B` or `b`: back up this conflict and all later conflicts for this run.

Backups are stored under `~/.local/state/dotfiles/backups/<timestamp>/`.

Preview changes without touching files:

```sh
./stow.sh --dry-run --packages zsh,tmux
```

Run local safety checks:

```sh
./scripts/check-dotfiles
```
