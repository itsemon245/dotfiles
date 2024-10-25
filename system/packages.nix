{config, lib, pkgs, user, system, ...}:
{
  environment.systemPackages = with pkgs; [
    vim
    neovim
    lua
    stylua
    unzip
    zsh
    git
    gcc
    ripgrep
    vscode
    tmux
    kitty
    pavucontrol
    pulseaudio
    gnome.nautilus
    cinnamon.nemo-with-extensions
    gparted
    vlc
    zoom-us
    incron
    distrobox
    podman
    postman
    google-chrome
    # Download Managers
    motrix
  ];
}
