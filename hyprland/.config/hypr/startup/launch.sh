#!/usr/bin/env bash

#Start wallpaper daemon
swww-daemon &
swww img ~/Wallpapers/default.jpg &

#Network Manager Applet
nm-applet --indicator &

#Launch waybar
waybar &

#Ibus Input Preference
ibus exit || true
ibus-daemon -d --replace &
ibus restart &

openrgb -p static.orp &

#Notification daemon
dunst &
