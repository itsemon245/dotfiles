#!/bin/bash

cpu_percent=(
  label.font="$FONT:Heavy:12"
  label=CPU
  label.color=$RED
  icon.color=$RED
  padding_left=10
  icon="$CPU"
  update_freq=5
  script="$PLUGIN_DIR/cpu.sh"
)

sketchybar --add item cpu.percent right          \
           --set cpu.percent "${cpu_percent[@]}"
