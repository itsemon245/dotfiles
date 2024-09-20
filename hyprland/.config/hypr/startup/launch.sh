#!/usr/bin/env bash

#Start wallpaper daemon
hyprpaper &

#Network Manager Applet
nm-applet --indicator &


#Notification daemon
mako

./waybar.sh
