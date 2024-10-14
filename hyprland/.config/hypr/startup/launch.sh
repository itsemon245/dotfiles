#!/usr/bin/env bash

#Start wallpaper daemon
swww-daemon &
swww img ~/Wallpapers/forest-mountain.png &

#Network Manager Applet
nm-applet --indicator &


#Notification daemon
mako

#./waybar.sh
