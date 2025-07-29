#!/bin/bash

calendar=(
  icon=cal
  icon.font="$FONT:Bold:12"
  icon.padding_left=$PADDINGS
  icon.padding_right=$GAP
  label.font="$FONT:Heavy:13"
  label.align=right
  label.padding_left=$GAP
  label.padding_right=$PADDINGS
  update_freq=30
  script="$PLUGIN_DIR/calendar.sh"
  click_script="$PLUGIN_DIR/zen.sh"
)

sketchybar --add item calendar right       \
           --set calendar "${calendar[@]}" \
           --subscribe calendar system_woke
