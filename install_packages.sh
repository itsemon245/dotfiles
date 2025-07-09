#!/usr/bin/env bash
source colors.sh
#Install Packages
echo "Installing Packages..."
#!/bin/bash

# Prompt for sudo password at the beginning
sudo -v

#Ask for the package manager user wants to use
function detect_package_manager(){
    if command -v apt &> /dev/null; then
        echo "apt"
    elif command -v pacman &> /dev/null; then
        echo "pacman"
    elif command -v dnf &> /dev/null; then
        echo "dnf"
    else
        echo -e "${RED}No supported package manager found!${NC}"
        exit 1
    fi
}

DETECTED_PACKAGE_MANAGER=$(detect_package_manager)
read -p "Enter the package manager you want to use (apt, pacman, dnf etc): [${DETECTED_PACKAGE_MANAGER}] " package_manager
package_manager=${package_manager:-$DETECTED_PACKAGE_MANAGER}

# Map of packages for different package managers
# Format: [package]=apt_name|pacman_name|dnf_name
declare -A package_map=(
    [kitty]="kitty|kitty|kitty"
    [tmux]="tmux|tmux|tmux"
    [zsh]="zsh|zsh|zsh"
    [git]="git|git|git"
    [php]="php|php|php"
    [composer]="composer|composer|composer"
    [golang]="golang|go|golang"
)

# List of required packages
packages=(kitty tmux zsh git php composer golang)

function get_package_name() {
    local pkg=$1
    local idx=0
    case $package_manager in
        apt) idx=0;;
        pacman) idx=1;;
        dnf) idx=2;;
        *) echo -e "${RED}Unsupported package manager: $package_manager${NC}"; exit 1;;
    esac
    IFS='|' read -ra names <<< "${package_map[$pkg]}"
    echo "${names[$idx]}"
}

function install_command(){
    local pkgs=()
    for pkg in "${packages[@]}"; do
        pkgs+=("$(get_package_name $pkg)")
    done
    case $package_manager in
        apt)
            echo "apt update && apt install -y ${pkgs[*]}"
            ;;
        pacman)
            echo "pacman -Sy --noconfirm ${pkgs[*]}"
            ;;
        dnf)
            echo "dnf install -y ${pkgs[*]}"
            ;;
        *)
            echo -e "${RED}Unsupported package manager: $package_manager${NC}"
            exit 1
            ;;
    esac
}

#Install Packages
echo -e "${CYAN}Installing packages: ${packages[*]} using $package_manager...${NC}"
sudo bash -c "$(install_command)"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}All packages installed successfully!${NC}"
else
    echo -e "${RED}Package installation failed!${NC}"
    exit 1
fi

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

