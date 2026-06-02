# Startup-safe environment helpers for bash and zsh.

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

is_interactive() {
    case "$-" in
        *i*) return 0 ;;
        *) return 1 ;;
    esac
}

has_display() {
    [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]
}
