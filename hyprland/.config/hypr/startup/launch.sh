#!/usr/bin/env bash

#Start wallpaper daemon
swww-daemon &
swww img ~/Wallpapers/default.jpg &

#Network Manager Applet
nm-applet --indicator &


#Notification daemon
dunst &

#Launch waybar
waybar &

ibus exit || true
ibus-daemon -d --replace &

greenclip daemon &
