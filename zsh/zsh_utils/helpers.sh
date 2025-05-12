#!/bin/bash
 # Colors
  local BOLD="\033[1m"
  local GREEN="\033[1;32m"
  local RED="\033[1;31m"
  local CYAN="\033[1;36m"
  local RESET="\033[0m"

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

ask() {
  local prompt="$1"
  local __resultvar="$2"
  local default="$3"
  local input

  # Colors
  local BOLD="\033[1m"
  local GREEN="\033[1;32m"
  local YELLOW="\033[1;33m"
  local RESET="\033[0m"

  # Prompt with color and default
  if [ -n "$default" ]; then
    printf "${BOLD}${GREEN}%s ${YELLOW}[%s]${RESET}: " "$prompt" "$default"
  else
    printf "${BOLD}${GREEN}%s${RESET}: " "$prompt"
  fi

  read input
  input="${input:-$default}"

  # Store result in provided variable
  if [ -n "$__resultvar" ]; then
    eval $__resultvar="'$input'"
  else
    echo "$input"
  fi
}

#Switch php version by changing the symlink
switchphp() {
  local DEFAULT_VERSION="81"
  local VERSION

  if [ -z "$1" ]; then
    ask "PHP version to switch to" VERSION "$DEFAULT_VERSION"
  else
    VERSION="$1"
  fi

  if [ ! -f "/usr/bin/php$VERSION" ]; then
    echo -e "${BOLD}${RED}❌ PHP version php$VERSION not found in /usr/bin/${RESET}"
    return 1
  fi

  echo -e "${BOLD}${CYAN}🔁 Switching to PHP $VERSION...${RESET}"
  sudo ln -sf "/usr/bin/php$VERSION" /usr/bin/php

  echo -e "${BOLD}${GREEN}✅ Now using:$RESET $(php -v | head -n1)"
}
