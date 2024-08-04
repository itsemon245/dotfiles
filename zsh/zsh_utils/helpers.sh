#!/bin/bash

# Function to source every file in a directory
# Usage: source_files_in directory_path
source_files_in() {
    local directory="$1"

    # Check if the directory exists
    if [ ! -d "$directory" ]; then
        echo "Error: Directory '$directory' not found."
        return 1
    fi

    # Loop through each file in the directory
    for file in "$directory"/*; do
        # Check if the file is a regular file and is readable
        if [ -f "$file" ] && [ -r "$file" ]; then
            # Source the file
            source "$file"
        fi
    done
}

# Function to set environment variables in a .env file
# Usage: setenv KEY=VALUE [ENV_FILE_PATH]
#   KEY=VALUE: The environment variable to set, in the format "KEY=VALUE"
#   ENV_FILE_PATH (optional): Path to the .env file (default is .env)
setenv() {
    if [ -z "$1" ]; then
        echo "Usage: setenv KEY=VALUE [ENV_FILE_PATH]"
        return 1
    fi

    local key=$(echo "$1" | awk -F= '{print toupper($1)}')
    local value=$(echo "$1" | cut -d= -f2-)
    local env_file=".env"
    
    if [ ! -z "$2" ]; then
        env_file="$2"
    fi

    sed -i "s/^\($key=\).*/\1$value/" "$env_file"
}
#Make a directory and cd into it
mkcd(){
  mkdir -p "$1"
  cd "$1"
}
