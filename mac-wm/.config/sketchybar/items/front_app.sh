#!/bin/bash

FRONT_APP_SCRIPT='sketchybar --set $NAME label="$INFO"'

yabai=(
  script="$PLUGIN_DIR/yabai.sh"
  icon.font="$FONT:Bold:16.0"
  icon.width=30
  icon=$YABAI_GRID
  icon.color=$ORANGE
  icon.padding_left=$PADDINGS
  icon.padding_right=$PADDINGS
  label.drawing=off
  associated_display=active
)

front_app=(
  script="$FRONT_APP_SCRIPT"
  icon=$YABAI_GRID
  icon.color=$ORANGE
  label.color=$WHITE
  label.font="$FONT:Heavy:12.0"
  icon.padding_right=$GAP
  label.padding_left=$GAP
  icon.padding_left=$PADDINGS
  label.padding_right=$PADDINGS
  associated_display=active
)

sketchybar --add event window_focus            \
           --add event windows_on_spaces       \
           --add item front_app left           \
           --set front_app "${front_app[@]}"   \
           --subscribe front_app front_app_switched

