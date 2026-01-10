#!/usr/bin/env bash
source colors.sh

# Check if git is installed, install if not
if ! command -v git &>/dev/null; then
    echo "Git not found. Installing git..."
    # Detect package manager and install git
    if command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm git
    elif command -v apt-get &>/dev/null; then
        sudo apt-get update && sudo apt-get install -y git
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y git
    elif command -v yum &>/dev/null; then
        sudo yum install -y git
    else
        echo "Error: Could not detect package manager. Please install git manually."
        exit 1
    fi
fi

# Check if we're already inside the dotfiles directory
if [ -d ".git" ] && [ -f "pocman/bin/pocman" ]; then
    echo "Already inside dotfiles directory. Skipping clone."
    DOTFILES_DIR="$(pwd)"
else
    # Clone dotfiles only if not already in dotfiles directory
    if [ ! -d ~/dotfiles ]; then
        git clone https://github.com/itsemon245/dotfiles.git ~/dotfiles
    fi
    DOTFILES_DIR=~/dotfiles
fi

cd "$DOTFILES_DIR"

./pocman/bin/pocman install stow
rm -rf ~/.config/pocman
source stow.sh
# Install all packages from TOML file using pkg script
./pocman/bin/pocman --all

echo -e "${CYAN}Updating SDDM theme...${NC}"
chmod +x ~/dotfiles/sddm/update.sh
source ~/dotfiles/sddm/update.sh
echo -e "${GREEN}SDDM theme updated successfully!${NC}"

rm -f ~/.zshrc
source nvm-setup.sh
source zsh-setup.sh
