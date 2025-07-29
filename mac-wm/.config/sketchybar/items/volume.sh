#!/bin/bash

volume_slider=(
  script="$PLUGIN_DIR/volume.sh"
  updates=on
  label.drawing=off
  background.padding_left=0
  icon.drawing=off
  slider.highlight_color=$BLUE
  slider.background.height=5
  slider.background.corner_radius=3
  slider.background.color=$BACKGROUND_2
  slider.knob=􀀁
  slider.knob.drawing=off
)

volume_icon=(
  click_script="$PLUGIN_DIR/volume_click.sh"
  icon.drawing=off
  icon.width=0
  background.padding_right=0
  label.align=left
  label.font="$FONT:Regular:14.0"
  label.padding_left=$PADDINGS
  label.padding_right=$PADDINGS
)

sketchybar --add slider volume right            \
           --set volume "${volume_slider[@]}"   \
           --subscribe volume volume_change     \
                              mouse.clicked     \
                              mouse.entered     \
                              mouse.exited      \
                                                \
           --add item volume_icon right         \
           --set volume_icon "${volume_icon[@]}"
