#!/bin/bash

POPUP_CLICK_SCRIPT="sketchybar --set \$NAME popup.drawing=toggle"

github_bell=(
  update_freq=180
  icon.font="$FONT:Bold:15.0"
  icon=$BELL
  icon.color=$BLUE
  icon.padding_left=$PADDINGS
  icon.padding_right=$GAP
  label=$LOADING
  label.highlight_color=$BLUE
  label.padding_left=$GAP
  label.padding_right=$PADDINGS
  popup.align=right
  script="$PLUGIN_DIR/github.sh"
  click_script="$POPUP_CLICK_SCRIPT"
)

github_template=(
  drawing=off
  background.corner_radius=12
  icon.padding_left=$PADDINGS
  icon.padding_right=$PADDINGS
  icon.background.height=2
  icon.background.y_offset=-12
)

sketchybar --add item github.bell right                 \
           --set github.bell "${github_bell[@]}"        \
           --subscribe github.bell  mouse.entered       \
                                    mouse.exited        \
                                    mouse.exited.global \
                                                        \
           --add item github.template popup.github.bell \
           --set github.template "${github_template[@]}"
