#!/usr/bin/env bash

DEVICES=(
    "Lian Li Uni Hub"
)

for device in "${DEVICES[@]}"; do
  openrgb -d "$device" -c {{color4 | strip}}
done
