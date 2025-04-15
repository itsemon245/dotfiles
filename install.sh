#!/usr/bin/env bash

# Installs dotfiles

git clone https://github.com/itsemon245/dotfiles.git ~/dotfiles
cd ~/dotfiles
echo -e "Installing dotfiles ...\n"
# Function to list directory names, excluding those in .stow-local-ignore
list_dir() {
    find . -maxdepth 1 -mindepth 1 -type d | sed "s|^\./||" | sort -h | grep -v -x -f ./.installignore
}

# List all directories and store them in a variable
directories=$(list_dir)

# Loop through each directory and stow it
echo "$directories" | while read -r dir; do
    echo "Stowing $dir ..."
    stow "$dir"
done
echo "Done!"

#Install Packages
echo "Installing Packages..."
#!/bin/bash

# Prompt for sudo password at the beginning
sudo -v

# Update package databases
sudo pacman -Sy

# Install pacman packages
sudo pacman -S --noconfirm \
alacritty arch-install-scripts atkinson-hyperlegible-fonts bat bind \
bluez bluez-utils btop cheese code feh fish fzf fuse2 gimp gnome-keyring \
grim gvfs gvfs-mtp helix htop hunspell hunspell-en_us hyprland kitty light \
linux-headers lsd man man-pages man-pages-posix mlocate mpv neofetch neovim \
networkmanager noto-fonts noto-fonts-emoji npm ntfs-3g openssh os-prober \
pacman-contrib pavucontrol pcmanfm polkit-gnome python python-pip ripgrep \
rofi rsync rustup sd snapd slurp sof-firmware swww texlive-core tldr tree \
ttf-firacode-nerd ttf-font-awesome ttf-jetbrains-mono \
ttf-nerd-fonts-symbols-common tumbler unrar unzip usbutils vim virt-manager \
wget wireplumber xdg-user-dirs xdg-utils xf86-video-amdgpu xorg xorg-xinit \
zip zsh

# Install required build tools
sudo pacman -S --noconfirm --needed git base-devel

# Install yay
git clone -q https://aur.archlinux.org/yay.git /tmp/yay
cd /tmp/yay
makepkg -si --noconfirm --needed
cd - >/dev/null
rm -rf /tmp/yay

# Install paru using yay
yay -S --noconfirm paru

# Install AUR packages
paru -S --noconfirm \
google-chrome hypridle hyprlock hyprpaper noisetorch paru-bin spotify \
swaylock-effects tela-icon-theme-git visual-studio-code-bin wob

echo "All packages installed successfully!"
