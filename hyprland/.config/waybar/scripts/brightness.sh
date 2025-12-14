#!/bin/bash

# Get brightness percentage from brightnessctl
# Try to find a backlight device first
backlight_device=$(brightnessctl -l 2>/dev/null | grep -iE "backlight|acpi_video|intel_backlight|amdgpu_bl" | head -1 | awk '{print $2}' | tr -d "'")

if [ -n "$backlight_device" ]; then
    # Use the found backlight device
    brightness=$(brightnessctl -d "$backlight_device" get 2>/dev/null)
    max=$(brightnessctl -d "$backlight_device" max 2>/dev/null)
    device_flag="-d $backlight_device"
else
    # Fallback: try to get any brightness device (might be LED)
    brightness=$(brightnessctl get 2>/dev/null)
    max=$(brightnessctl max 2>/dev/null)
    device_flag=""
fi

if [ -n "$brightness" ] && [ -n "$max" ] && [ "$max" -gt 0 ]; then
    percent=$((brightness * 100 / max))
    # Output JSON for waybar
    echo "{\"text\": \"$percent\", \"percentage\": $percent, \"class\": \"backlight\"}"
else
    echo ""
fi
