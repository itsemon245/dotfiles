#!/usr/bin/env bash

# Installs dotfiles
git clone https://github.com/itsemon245/dotfiles.git ~/.dotfiles
cd ~/.dotfiles
echo -e "Installing dotfiles ...\n"
nix-shell -p stow coreutils gawk --pure --run 'sh <<EOF
# Function to list directory names, excluding those in .stow-local-ignore
list_dir() {
    find . -maxdepth 1 -mindepth 1 -type d | sed "s|^\./||" | sort -h | grep -v -x -f ./.installignore
}

# List all directories and store them in a variable
directories=\$(list_dir)

# Loop through each directory and stow it
echo "\$directories" | while read -r dir; do
    echo "Stowing \$dir ..."
    stow "\$dir"
done
EOF'
echo "Done!"
