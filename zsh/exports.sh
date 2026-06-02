#!/usr/bin/env bash

if ! command -v path_prepend >/dev/null 2>&1; then
    _dotfiles_shell_helpers="${DOTFILES_SHELL_HELPERS:-$HOME/.local/lib/dotfiles/shell/common.sh}"
    if [[ -r "$_dotfiles_shell_helpers" ]]; then
        # shellcheck source=/dev/null
        . "$_dotfiles_shell_helpers"
    fi
    unset _dotfiles_shell_helpers
fi

if ! command -v path_prepend >/dev/null 2>&1; then
    path_contains() {
        case ":${PATH:-}:" in
            *":$1:"*) return 0 ;;
            *) return 1 ;;
        esac
    }

    path_prepend() {
        [[ -n "${1:-}" ]] || return 0
        path_contains "$1" && return 0
        PATH="$1${PATH:+:$PATH}"
    }

    path_append() {
        [[ -n "${1:-}" ]] || return 0
        path_contains "$1" && return 0
        PATH="${PATH:+$PATH:}$1"
    }
fi

path_prepend "$HOME/env/bin"
path_prepend "$HOME/bin"
path_prepend "$HOME/.local/bin"
path_append "/usr/local/bin"
path_append "$HOME/.config/composer/vendor/bin"
path_append "/opt/nvim-linux64/bin"
path_append "$HOME/.local/share/bin"
path_append "$HOME/.local/share/nvim/mason/bin"
path_append "$HOME/.local/share/nvim/lazy/none-ls.nvim/lua/null-ls/builtins/diagnostics"
path_append "$HOME/scripts"

export PATH

export GTK_IM_MODULE=ibus
export XMODIFIERS=@im=ibus
export QT_IM_MODULE=ibus
export NIX_REMOTE=daemon

# NVM is optional; when present it manages the active Node version in PATH.
export NVM_DIR="$HOME/.nvm"
if [[ -s "$NVM_DIR/nvm.sh" ]] && ! command -v nvm >/dev/null 2>&1; then
    # shellcheck source=/dev/null
    . "$NVM_DIR/nvm.sh"
fi
if [[ -s "$NVM_DIR/bash_completion" ]]; then
    # shellcheck source=/dev/null
    . "$NVM_DIR/bash_completion"
fi

# Android SDK
export ANDROID_HOME=/opt/android-sdk
path_append "$ANDROID_HOME/emulator"
path_append "$ANDROID_HOME/platform-tools"
path_append "$ANDROID_HOME/tools"
path_append "$ANDROID_HOME/tools/bin"
export PATH
