#!/bin/bash

netspeed=(
  icon="$NETSPEED"
  icon.font="$FONT:Heavy:12"
  icon.color=$GREEN
  icon.padding_left=$PADDINGS
  icon.padding_right=$GAP
  label.color=$GREEN
  label.font="$FONT:Heavy:12"
  label="N/A"
  label.align=left
  label.padding_left=$GAP
  label.padding_right=$PADDINGS
  update_freq=2
  script="$PLUGIN_DIR/netspeed.sh"
)

sketchybar --add item netspeed right \
           --set netspeed "${netspeed[@]}"

