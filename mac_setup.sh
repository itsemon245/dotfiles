#!/usr/bin/env bash
source colors.sh

# Installs dotfiles for macOS

echo -e "${CYAN}Setting up dotfiles for macOS...${NC}"

# Check if Homebrew is installed
if ! command -v brew &> /dev/null; then
    echo -e "${YELLOW}Homebrew not found. Installing Homebrew...${NC}"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    # Add Homebrew to PATH for Apple Silicon Macs
    if [[ $(uname -m) == "arm64" ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
else
    echo -e "${GREEN}Homebrew already installed.${NC}"
fi

# Clone dotfiles if not already present
if [ ! -d ~/dotfiles ]; then
    echo -e "${CYAN}Cloning dotfiles...${NC}"
    git clone https://github.com/itsemon245/dotfiles.git ~/dotfiles
else
    echo -e "${GREEN}Dotfiles already cloned.${NC}"
fi

cd ~/dotfiles

# Install packages using Homebrew
echo -e "${CYAN}Installing packages with Homebrew...${NC}"
source mac_install_packages.sh

# Remove existing .zshrc if present
rm -f ~/.zshrc

# Run the rest of the setup
echo -e "${CYAN}Running dotfiles setup...${NC}"
source update.sh
source zsh-setup.sh
source ~/.zshrc
source nvm-setup.sh

echo -e "${GREEN}macOS setup completed successfully!${NC}"
echo -e "${YELLOW}Please restart your terminal or run 'source ~/.zshrc' to apply changes.${NC}"
