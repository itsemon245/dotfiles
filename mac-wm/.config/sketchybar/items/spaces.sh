#!/bin/bash

sketchybar --add event aerospace_workspace_change

for sid in $(aerospace list-workspaces --all); do
    space=(
        background.drawing=on
        background.height=26
        background.drawing=on
        background.corner_radius=8
        background.padding_left=2
        background.padding_right=2
        label="$sid"
        icon.drawing=off
        label.padding_left=8
        label.padding_right=8
        icon.width=0
        label.font="$FONT:Heavy:14.0"
        click_script="aerospace workspace $sid"
        script="$PLUGIN_DIR/aerospace.sh $sid"
    )

    sketchybar --add item space.$sid left \
        --subscribe space.$sid aerospace_workspace_change \
        --set space.$sid "${space[@]}"
done