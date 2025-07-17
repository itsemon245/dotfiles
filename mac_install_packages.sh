#!/usr/bin/env bash
source colors.sh

# Install Packages for macOS using Homebrew
echo -e "${CYAN}Installing packages for macOS...${NC}"

# Check if Homebrew is available
if ! command -v brew &> /dev/null; then
    echo -e "${RED}Homebrew is not installed or not in PATH!${NC}"
    echo -e "${YELLOW}Please install Homebrew first or run mac_setup.sh which will install it automatically.${NC}"
    exit 1
fi

# Update Homebrew
echo -e "${CYAN}Updating Homebrew...${NC}"
brew update

# List of packages to install via Homebrew
packages=(
    "kitty"
    "tmux"
    "zsh"
    "git"
    "php"
    "composer"
    "go"
    "stow"
    "curl"
    "wget"
)

# Install packages
echo -e "${CYAN}Installing packages: ${packages[*]}...${NC}"
for package in "${packages[@]}"; do
    if brew list "$package" &>/dev/null; then
        echo -e "${GREEN}$package is already installed.${NC}"
    else
        echo -e "${CYAN}Installing $package...${NC}"
        brew install "$package"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}$package installed successfully!${NC}"
        else
            echo -e "${RED}Failed to install $package!${NC}"
        fi
    fi
done

# Install TPM for tmux if not present
echo -e "${CYAN}Checking for Tmux Plugin Manager (TPM)...${NC}"
if [ ! -d "$HOME/.tmux/plugins/tpm" ]; then
    echo -e "${YELLOW}TPM not found. Cloning TPM...${NC}"
    git clone https://github.com/tmux-plugins/tpm "$HOME/.tmux/plugins/tpm"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}TPM installed successfully!${NC}"
    else
        echo -e "${RED}Failed to install TPM!${NC}"
    fi
else
    echo -e "${GREEN}TPM already installed.${NC}"
fi

echo -e "${CYAN}Stowing...${NC}"
source ./update.sh

echo -e "${CYAN}Installing basic zsh plugins...${NC}"
git clone https://github.com/zsh-users/zsh-autosuggestions.git $ZSH_CUSTOM/plugins/zsh-autosuggestions
git clone https://github.com/zsh-users/zsh-syntax-highlighting.git $ZSH_CUSTOM/plugins/zsh-syntax-highlighting


echo -e "${GREEN}All packages installed successfully!${NC}"
