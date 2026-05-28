#!/usr/bin/env bash

set -uo pipefail

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[0;33m'
CYAN=$'\033[0;36m'
NC=$'\033[0m'

install_git_if_missing() {
    if command -v git >/dev/null 2>&1; then
        return 0
    fi

    printf '%bGit not found. Installing git...%b\n' "$YELLOW" "$NC"

    if command -v pacman >/dev/null 2>&1; then
        sudo pacman -S --noconfirm git
    elif command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update
        sudo apt-get install -y git
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y git
    elif command -v yum >/dev/null 2>&1; then
        sudo yum install -y git
    else
        printf '%bError:%b could not detect a package manager. Install git manually.\n' "$RED" "$NC" >&2
        exit 1
    fi
}

resolve_dotfiles_dir() {
    if [[ -d ".git" && -x "pocman/bin/pocman" ]]; then
        pwd
        return 0
    fi

    local dotfiles_dir="${DOTFILES_DIR:-$HOME/dotfiles}"

    if [[ ! -d "$dotfiles_dir" ]]; then
        git clone https://github.com/itsemon245/dotfiles.git "$dotfiles_dir"
    fi

    printf '%s\n' "$dotfiles_dir"
}

install_git_if_missing

DOTFILES_DIR="$(resolve_dotfiles_dir)"
cd "$DOTFILES_DIR" || exit 1

if [[ -f "$DOTFILES_DIR/colors.sh" ]]; then
    # shellcheck source=/dev/null
    source "$DOTFILES_DIR/colors.sh"
fi

printf '%bInstalling stow...%b\n' "$CYAN" "$NC"
"$DOTFILES_DIR/pocman/bin/pocman" install stow

printf '%bStowing dotfiles...%b\n' "$CYAN" "$NC"
"$DOTFILES_DIR/stow.sh"

printf '%bInstalling packages from Pocman lists...%b\n' "$CYAN" "$NC"
"$DOTFILES_DIR/pocman/bin/pocman" --all

if [[ -x "$DOTFILES_DIR/sddm/update.sh" ]]; then
    printf '%bUpdating SDDM theme...%b\n' "$CYAN" "$NC"
    "$DOTFILES_DIR/sddm/update.sh"
    printf '%bSDDM theme updated successfully.%b\n' "$GREEN" "$NC"
fi

if [[ -x "$DOTFILES_DIR/nvm-setup.sh" ]]; then
    "$DOTFILES_DIR/nvm-setup.sh"
fi

if [[ -x "$DOTFILES_DIR/zsh-setup.sh" ]]; then
    "$DOTFILES_DIR/zsh-setup.sh"
fi
