#!/usr/bin/env bash
source colors.sh

# Installs dotfiles

git clone https://github.com/itsemon245/dotfiles.git ~/dotfiles

cd ~/dotfiles
source install_packages.sh
rm -f ~/.zshrc
source update.sh
source nvm-setup.sh
source zsh-setup.sh
