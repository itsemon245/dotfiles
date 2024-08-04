#!/bin/bash

# Array of directory names
list_dir(){
    find . -maxdepth 1 -not -path '*/\.*' -type d | awk -F/ '{print $2}' | sort -h
}

# List All directories and store them in a variable
directories=($(list_dir))

# Loop through each directory and stow it
for dir in "${directories[@]}"; do
    echo "Stowing $dir ..."
    stow "$dir"
done
