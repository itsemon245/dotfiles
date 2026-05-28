#!/usr/bin/env bash

set -uo pipefail

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[0;33m'
CYAN=$'\033[0;36m'
NC=$'\033[0m'

printf '%bSetting up dotfiles for macOS...%b\n' "$CYAN" "$NC"

if ! command -v brew >/dev/null 2>&1; then
    printf '%bHomebrew not found. Installing Homebrew...%b\n' "$YELLOW" "$NC"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    if [[ "$(uname -m)" == "arm64" ]]; then
        printf '%s\n' 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zprofile"
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    printf '%bHomebrew already installed.%b\n' "$GREEN" "$NC"
fi

DOTFILES_DIR="${DOTFILES_DIR:-$HOME/dotfiles}"

if [[ ! -d "$DOTFILES_DIR" ]]; then
    printf '%bCloning dotfiles...%b\n' "$CYAN" "$NC"
    git clone https://github.com/itsemon245/dotfiles.git "$DOTFILES_DIR"
else
    printf '%bDotfiles already cloned.%b\n' "$GREEN" "$NC"
fi

cd "$DOTFILES_DIR" || exit 1

if [[ -f "$DOTFILES_DIR/colors.sh" ]]; then
    # shellcheck source=/dev/null
    source "$DOTFILES_DIR/colors.sh"
fi

printf '%bInstalling packages with Homebrew...%b\n' "$CYAN" "$NC"
"$DOTFILES_DIR/mac_install_packages.sh"

printf '%bStowing macOS dotfiles...%b\n' "$CYAN" "$NC"
"$DOTFILES_DIR/stow.sh" --packages zsh,tmux,nvim,vim,mac-wm,others,composer,fonts

if [[ -x "$DOTFILES_DIR/nvm-setup.sh" ]]; then
    "$DOTFILES_DIR/nvm-setup.sh"
fi

if [[ -x "$DOTFILES_DIR/zsh-setup.sh" ]]; then
    "$DOTFILES_DIR/zsh-setup.sh"
fi

printf '%bmacOS setup completed successfully.%b\n' "$GREEN" "$NC"
printf '%bRestart your terminal or run `source ~/.zshrc` to apply changes.%b\n' "$YELLOW" "$NC"
