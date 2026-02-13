#!/usr/bin/env bash

# -----------------------------------------------------
# System Services (Standard Launch)
# -----------------------------------------------------
swww-daemon &
swww img ~/Wallpapers/default.png &
nm-applet --indicator &
ibus exit || true
ibus-daemon -d --replace &
ibus restart &
dunst &
waybar &


# -----------------------------------------------------
# RGB Stuffs
# -----------------------------------------------------
OPENRGB_SCRIPT="~/.config/OpenRGB/scripts/wallust-colors.sh"

if [ -f "$OPENRGB_SCRIPT" ] && command -v openrgb &> /dev/null; then
    bash "$OPENRGB_SCRIPT"
fi


# -----------------------------------------------------
# Silent Applications
# -----------------------------------------------------

# Siltently start slack
slack -u

# Silently start localsend
localsend --hidden



