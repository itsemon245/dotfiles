#!/bin/bash
# Full path to your download speed script
DOWNLOAD_SPEED_SCRIPT="$HOME/scripts/download_speed"

if [[ -x "$DOWNLOAD_SPEED_SCRIPT" ]]; then
  SPEED=$("$DOWNLOAD_SPEED_SCRIPT")
  sketchybar --set netspeed label="$SPEED"
else
  sketchybar --set netspeed label="N/A"
fi

