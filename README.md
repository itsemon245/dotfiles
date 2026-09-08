## Getting Started

### One Liner installation
```sh
sh <(curl -sL https://itsemon245.github.io/dotfiles/install.sh)
```

### System-wide WirePlumber device policy

The WirePlumber device-priority rules are tracked in
`wireplumber/system/wireplumber.conf.d/`. They are intentionally not stowed
into a user's home directory: deploy them for every local user with:

```sh
./wireplumber/install-system-config.sh
```

Preview the deployment without administrator access:

```sh
./wireplumber/install-system-config.sh --dry-run
```

On a fresh installation, opt in to the same deployment with:

```sh
sh <(curl -sL https://itsemon245.github.io/dotfiles/install.sh) --system-audio
```

Users with an old `~/.config/wireplumber` stow symlink should remove that
link once after deploying the system configuration, then restart their
WirePlumber session or log out and back in.

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
