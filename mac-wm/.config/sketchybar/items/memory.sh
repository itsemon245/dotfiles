#!/bin/bash

memory_free=(
  icon="$MEMORY"
  icon.font="$FONT:Heavy:12"
  icon.color=$YELLOW
  icon.padding_left=$PADDINGS
  icon.padding_right=$GAP
  label.color=$YELLOW
  label.font="$FONT:Heavy:12"
  label="Memory"
  label.align=left
  label.padding_left=$GAP
  label.padding_right=$PADDINGS
  update_freq=5
  script="$PLUGIN_DIR/memory.sh"
)

sketchybar --add item memory.free right \
           --set memory.free "${memory_free[@]}"
