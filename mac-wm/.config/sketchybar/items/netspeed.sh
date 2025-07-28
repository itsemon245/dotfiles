#!/bin/bash

netspeed=(
  icon="$NETSPEED"
  icon.font="$FONT:Heavy:12"
  icon.color=$GREEN
  label.color=$GREEN
  label.font="$FONT:Heavy:12"
  label="DL"
  label.align=left
  padding_left=10
  update_freq=1
  script="$PLUGIN_DIR/netspeed.sh"
)

sketchybar --add item netspeed right \
           --set netspeed "${netspeed[@]}"

