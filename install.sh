#!/usr/bin/env bash
source colors.sh

# Installs dotfiles

git clone https://github.com/itsemon245/dotfiles.git ~/dotfiles

cd ~/dotfiles
# Install all packages from TOML file using pkg script
./others/bin/pkg --all
rm -f ~/.zshrc
source update.sh
source nvm-setup.sh
source zsh-setup.sh
