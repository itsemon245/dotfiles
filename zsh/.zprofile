# Login-shell environment.
#
# SDDM starts the graphical session through `zsh --login`, so Hyprland and
# everything it launches (keybindings, Waybar, menus) inherit this PATH.
# Keep this file dependency-free: it runs before any interactive setup.

typeset -U path PATH
path=("$HOME/.local/bin" $path)
export PATH
