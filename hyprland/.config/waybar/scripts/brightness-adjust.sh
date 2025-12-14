#!/bin/bash

# Adjust brightness up or down
# Usage: brightness-adjust.sh [+|-] [amount]

direction=${1:-+}
amount=${2:-5}

# Try to find a backlight device first
backlight_device=$(brightnessctl -l 2>/dev/null | grep -iE "backlight|acpi_video|intel_backlight|amdgpu_bl" | head -1 | awk '{print $2}' | tr -d "'")

if [ -n "$backlight_device" ]; then
    brightnessctl -d "$backlight_device" set "${direction}${amount}%" 2>/dev/null
else
    brightnessctl set "${direction}${amount}%" 2>/dev/null
fi
