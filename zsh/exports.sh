#!/usr/bin/env bash

export PATH="$HOME/bin:$HOME/env/bin:$/usr/local/bin:$PATH"
export PATH="$PATH:$HOME/.config/composer/vendor/bin"
export GTK_IM_MODULE=ibus
export XMODIFIERS=@im=ibus
export QT_IM_MODULE=ibus
export PATH="$PATH:/opt/nvim-linux64/bin"
export PATH="$PATH:$HOME/.local/bin"
export PATH="$PATH:$HOME/.local/share/bin"
export PATH="$PATH:$HOME/.local/share/nvim/mason/bin"
export PATH="$PATH:$HOME/.local/share/nvim/lazy/none-ls.nvim/lua/null-ls/builtins/diagnostics"
export PATH="$PATH:/opt/nvim-linux64/bin"
export PATH="$PATH:$HOME/scripts"

#Loads nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
#Sources Global Node Binaries
export PATH="$PATH:$HOME/.nvm/versions/node/v20.11.1/bin"
export QT_IM_MODULE=ibus
export NIX_REMOTE=daemon

# Android SDK
export ANDROID_HOME=/opt/android-sdk
export PATH=$PATH:$ANDROID_HOME/emulator
export PATH=$PATH:$ANDROID_HOME/platform-tools
export PATH=$PATH:$ANDROID_HOME/tools
export PATH=$PATH:$ANDROID_HOME/tools/bin

