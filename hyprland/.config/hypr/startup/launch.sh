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
openrgb -p static.orp &
dunst &
waybar &

# -----------------------------------------------------
# Silent Applications
# -----------------------------------------------------

# Siltently start slack
slack -u

# Silently start localsend
localsend --hidden
