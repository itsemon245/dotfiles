#!/bin/bash

memory_free=(
  icon="$MEMORY"
  icon.font="$FONT:Heavy:12"
  icon.color=$YELLOW
  label.color=$YELLOW
  label.font="$FONT:Heavy:12"
  label="Memory"
  label.align=left
  padding_left=10
  update_freq=5
  script="$PLUGIN_DIR/memory.sh"
)

sketchybar --add item memory.free right \
           --set memory.free "${memory_free[@]}"
