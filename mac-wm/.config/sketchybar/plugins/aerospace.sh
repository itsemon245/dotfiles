#!/usr/bin/env bash

export WHITE=0xffcad3f5
export RED=0xffed8796
if [ "$1" = "$FOCUSED_WORKSPACE" ]; then
    sketchybar --set $NAME label.color=$RED
else
    sketchybar --set $NAME label.color=$WHITE
fi
