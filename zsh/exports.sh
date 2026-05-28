#!/usr/bin/env bash

path_contains() {
    case ":$PATH:" in
        *":$1:"*) return 0 ;;
        *) return 1 ;;
    esac
}

path_prepend_once() {
    local entry="$1"

    [[ -n "$entry" ]] || return 0
    path_contains "$entry" && return 0
    PATH="$entry:$PATH"
}

path_append_once() {
    local entry="$1"

    [[ -n "$entry" ]] || return 0
    path_contains "$entry" && return 0
    PATH="$PATH:$entry"
}

path_prepend_once "$HOME/bin"
path_prepend_once "$HOME/env/bin"
path_append_once "/usr/local/bin"
path_append_once "$HOME/.config/composer/vendor/bin"
path_append_once "/opt/nvim-linux64/bin"
path_append_once "$HOME/.local/bin"
path_append_once "$HOME/.local/share/bin"
path_append_once "$HOME/.local/share/nvim/mason/bin"
path_append_once "$HOME/.local/share/nvim/lazy/none-ls.nvim/lua/null-ls/builtins/diagnostics"
path_append_once "$HOME/scripts"

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
path_append_once "$ANDROID_HOME/emulator"
path_append_once "$ANDROID_HOME/platform-tools"
path_append_once "$ANDROID_HOME/tools"
path_append_once "$ANDROID_HOME/tools/bin"
export PATH
