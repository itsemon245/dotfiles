#!/bin/bash

battery=(
  script="$PLUGIN_DIR/battery.sh"
  icon.font="$FONT:Regular:19.0"
  icon.padding_left=$PADDINGS
  icon.padding_right=$PADDINGS
  label.drawing=off
  update_freq=120
  updates=on
)

sketchybar --add item battery right      \
           --set battery "${battery[@]}" \
           --subscribe battery power_source_change system_woke
