#!/usr/bin/env bash
source colors.sh

# Installs dotfiles

git clone https://github.com/itsemon245/dotfiles.git ~/dotfiles

source update.sh
source install_packages.sh