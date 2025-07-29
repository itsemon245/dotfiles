#!/bin/bash

cpu_percent=(
  icon="$CPU"
  icon.color=$RED
  icon.padding_left=$PADDINGS
  icon.padding_right=$GAP
  label.font="$FONT:Heavy:12"
  label=CPU
  label.color=$RED
  label.padding_left=$GAP
  label.padding_right=$PADDINGS
  update_freq=5
  script="$PLUGIN_DIR/cpu.sh"
)

sketchybar --add item cpu.percent right          \
           --set cpu.percent "${cpu_percent[@]}"
