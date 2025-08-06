#!/usr/bin/env bash
set -euo pipefail

# Location of tmux config and TPM
TMUX_CONF="$HOME/.tmux.conf"
TPM_DIR="$HOME/.tmux/plugins/tpm"

# Determine the script directory (where this install script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMUX_DIR="$(dirname "$SCRIPT_DIR")"

# Base URL for raw GitHub files
BASE_URL="https://raw.githubusercontent.com/itsemon245/dotfiles/main/tmux"

# Main config file
TMUX_CONF_URL="$BASE_URL/.tmux.conf"

# Array of script files in tmux-scripts directory
TMUX_SCRIPTS=(
    "tmux-get-env"
)

# Choose downloader: prefer curl, fallback to wget
if command -v curl >/dev/null 2>&1; then
  DOWNLOADER="curl -fsSL -o"
elif command -v wget >/dev/null 2>&1; then
  DOWNLOADER="wget -qO"
else
  echo "Error: Neither curl nor wget found. Please install one." >&2
  exit 1
fi

# Check if ~/.tmux.conf already exists
if [[ -f "$TMUX_CONF" ]]; then
  echo "Warning: $TMUX_CONF already exists."
  read -p "Do you want to overwrite it? [y/N] " answer
  case "$answer" in
    [yY][eE][sS]|[yY])
      echo "Overwriting $TMUX_CONF..."
      ;;
    *)
      echo "Cancelled. Existing $TMUX_CONF was not changed."
      exit 0
      ;;
  esac
fi

echo "Downloading .tmux.conf to $TMUX_CONF"
$DOWNLOADER "$TMUX_CONF" "$TMUX_CONF_URL"

# Create tmux-scripts directory
TMUX_SCRIPTS_DIR="$HOME/.tmux-scripts"
echo "Creating tmux-scripts directory at $TMUX_SCRIPTS_DIR"
mkdir -p "$TMUX_SCRIPTS_DIR"

# Download tmux scripts from array
for script in "${TMUX_SCRIPTS[@]}"; do
  script_url="$BASE_URL/.tmux-scripts/$script"
  script_file="$TMUX_SCRIPTS_DIR/$script"
  
  echo "Downloading $script to $script_file"
  $DOWNLOADER "$script_file" "$script_url"
  
  # Make script executable
  echo "Making $script_file executable"
  chmod +x "$script_file"
done

# TPM installation
if [[ -d "$TPM_DIR" ]]; then
  echo "TPM already exists at $TPM_DIR. Skipping clone."
else
  echo "Cloning TPM into $TPM_DIR"
  git clone https://github.com/tmux-plugins/tpm "$TPM_DIR"
fi

echo "Done! Now start tmux and press 'prefix + I' to install plugins."

