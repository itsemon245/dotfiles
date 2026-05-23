#!/usr/bin/env bash

LOG_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/hypr"
LOG_FILE="$LOG_DIR/startup.log"
DEFAULT_WALLPAPER="$HOME/Wallpapers/default.png"
OPENRGB_SCRIPT="$HOME/.config/OpenRGB/scripts/wallust-colors.sh"
POLKIT_AGENT="/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1"
OPENWHISPR_BIN="/opt/openwhispr/open-whispr"

mkdir -p "$LOG_DIR"
: > "$LOG_FILE"

log() {
    printf '[%(%F %T)T] %s\n' -1 "$*" >> "$LOG_FILE"
}

notify() {
    local message="$1"
    local urgency="${2:-normal}"

    log "$message"

    if command -v dunstify >/dev/null 2>&1 && dunstify -a "Hyprland startup" -u "$urgency" "Hyprland startup" "$message" >/dev/null 2>&1; then
        return
    fi

    if command -v notify-send >/dev/null 2>&1 && notify-send -a "Hyprland startup" -u "$urgency" "Hyprland startup" "$message" >/dev/null 2>&1; then
        return
    fi

    if command -v hyprctl >/dev/null 2>&1 && hyprctl notify -1 5000 "rgb(ffb86c)" "$message" >/dev/null 2>&1; then
        return
    fi

    printf 'Hyprland startup: %s\n' "$message" >&2
}

have() {
    local command="$1"
    local label="$2"

    command -v "$command" >/dev/null 2>&1 && return 0
    notify "Skipped $label: missing command '$command'." critical
    return 1
}

already_running() {
    command -v pgrep >/dev/null 2>&1 && pgrep "$@" >/dev/null 2>&1
}

start_dunst() {
    have dunst "notification daemon" || return
    already_running -x dunst && return

    log "Starting notification daemon: dunst"
    dunst >> "$LOG_FILE" 2>&1 &
    sleep 0.3
}

spawn() {
    local label="$1"
    local process="$2"
    shift 2

    have "$1" "$label" || return
    if already_running -x "$process"; then
        log "$label already running; skipping."
        return
    fi

    log "Starting $label: $*"
    "$@" >> "$LOG_FILE" 2>&1 &
}

spawn_path() {
    local label="$1"
    local path="$2"
    shift 2

    if [[ ! -x "$path" ]]; then
        notify "Skipped $label: executable not found at $path." critical
        return
    fi

    if already_running -f "$path"; then
        log "$label already running; skipping."
        return
    fi

    log "Starting $label: $path${*:+ $*}"
    "$path" "$@" >> "$LOG_FILE" 2>&1 &
}

run() {
    local label="$1"
    shift

    have "$1" "$label" || return
    log "Running $label: $*"

    "$@" >> "$LOG_FILE" 2>&1 || notify "$label failed. See $LOG_FILE." critical
}

set_wallpaper() {
    have awww-daemon "wallpaper daemon" || return
    have awww "wallpaper" || return

    spawn "wallpaper daemon" awww-daemon awww-daemon
    sleep 0.3

    if [[ -f "$DEFAULT_WALLPAPER" ]]; then
        run "wallpaper" awww img "$DEFAULT_WALLPAPER"
    else
        notify "Skipped wallpaper: missing file $DEFAULT_WALLPAPER." critical
    fi
}

start_ibus() {
    have ibus "IBus" || return
    have ibus-daemon "IBus daemon" || return

    ibus exit >> "$LOG_FILE" 2>&1 || true
    spawn "IBus daemon" ibus-daemon ibus-daemon -d --replace
    run "IBus restart" ibus restart
}

sync_openrgb_theme() {
    if [[ ! -f "$OPENRGB_SCRIPT" ]]; then
        notify "Skipped OpenRGB theme sync: missing script $OPENRGB_SCRIPT." normal
        return
    fi

    have openrgb "OpenRGB theme sync" && run "OpenRGB theme sync" bash "$OPENRGB_SCRIPT"
}

start_dunst

spawn_path "polkit authentication agent" "$POLKIT_AGENT"
set_wallpaper
spawn "NetworkManager applet" nm-applet nm-applet --indicator
start_ibus
spawn "Waybar" waybar waybar

sync_openrgb_theme

spawn "Slack" slack slack -u
spawn "LocalSend" localsend localsend --hidden
spawn_path "OpenWhispr" "$OPENWHISPR_BIN" --no-sandbox
