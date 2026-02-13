#!/usr/bin/env bash

# -----------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------
LOCK_FILE="/tmp/hypr_focus_mode_active"

# -----------------------------------------------------
# LOGIC
# -----------------------------------------------------

if [ -f "$LOCK_FILE" ]; then
    # =====================================================
    # TOGGLE OFF (RESTORE)
    # =====================================================

    # 1. Remove the lock file
    rm "$LOCK_FILE"

    # 2. Reload Hyprland
    #    This clears all dynamic 'keyword' rules we added.
    #    The window returns to using decoration.conf settings.
    hyprctl reload

    notify-send \
        -i "view-refresh" \
        -a "Hyprland" \
        -r 9999 \
        "Restored" \
        "Window visual effects reset."

else
    # =====================================================
    # TOGGLE ON (ACTIVE WINDOW ONLY)
    # =====================================================

    # 1. Get the Active Window Address
    addr=$(hyprctl activewindow -j | jq -r '.address')

    if [ "$addr" == "null" ] || [ -z "$addr" ]; then
        notify-send "Hyprland" "No active window selected."
        exit 0
    fi

    # 2. Create lock file
    touch "$LOCK_FILE"

    # 3. Inject Rules SPECIFIC to this Address
    #    "opacity 1 override 1 override" -> Force 1.0 opacity (ignoring active_opacity)
    #    "noblur" -> Disable blur for this window only

    hyprctl keyword windowrulev2 "opacity 1 override 1 override, address:$addr"
    hyprctl keyword windowrulev2 "noblur, address:$addr"

    notify-send \
        -i "video-display" \
        -a "Hyprland" \
        -r 9999 \
        "Focus Mode" \
        "Active window is now solid."
fi
#!/usr/bin/env bash

# -----------------------------------------------------
# CHECK CURRENT STATE
# -----------------------------------------------------
# We check if blur is currently enabled (1 = enabled, 0 = disabled)
# This serves as our toggle switch.
current_blur=$(hyprctl getoption decoration:blur:enabled -j | jq '.int')

if [ "$current_blur" == "1" ]; then
    # =====================================================
    # ENABLE FOCUS MODE (Clean, Opaque, Sharp)
    # =====================================================

    # 1. Disable Blur globally
    hyprctl keyword decoration:blur:enabled false

    # 2. Force Opacity to 1.0 globally
    #    This overrides the 0.75/0.5 in your decoration.conf
    hyprctl keyword decoration:active_opacity 1.0
    hyprctl keyword decoration:inactive_opacity 1.0

    # 3. Optional: Add a subtle border color change to indicate mode
    hyprctl keyword general:col.active_border "rgba(00ff00ee)"

    notify-send \
        -i "video-display" \
        -a "Hyprland" \
        -r 9999 \
        "Focus Mode Enabled" \
        "Opacity: 1.0 | Blur: 0"

else
    # =====================================================
    # DISABLE FOCUS MODE (Restore Config)
    # =====================================================

    # Reloading forces Hyprland to re-read your decoration.conf
    # This automatically reverts all the keyword changes above.
    hyprctl reload

    notify-send \
        -i "video-display" \
        -a "Hyprland" \
        -r 9999 \
        "Focus Mode Disabled" \
        "Restored from config"
fi
