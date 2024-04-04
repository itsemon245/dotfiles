#!/bin/bash

# Array of directory names
directories=(
    "bash"
    "composer"
    "customization"
    "kitty"
    "nvim"
    "others"
    "tmux"
    "vim"
    "zsh"
)

# Loop through each directory and stow it
for dir in "${directories[@]}"; do
    stow "$dir"
    echo "Stowed $dir"
done
