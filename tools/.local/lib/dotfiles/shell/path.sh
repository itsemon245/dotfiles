# Startup-safe PATH helpers for bash and zsh.

path_contains() {
    local entry="${1:-}"

    [ -n "$entry" ] || return 1
    case ":${PATH:-}:" in
        *":$entry:"*) return 0 ;;
        *) return 1 ;;
    esac
}

path_prepend() {
    local entry="${1:-}"

    [ -n "$entry" ] || return 0
    path_contains "$entry" && return 0
    PATH="$entry${PATH:+:$PATH}"
}

path_append() {
    local entry="${1:-}"

    [ -n "$entry" ] || return 0
    path_contains "$entry" && return 0
    PATH="${PATH:+$PATH:}$entry"
}

path_remove() {
    local remove="${1:-}"
    local remaining="${PATH:-}:"
    local entry
    local new_path=""

    [ -n "$remove" ] || return 0

    while [ -n "$remaining" ]; do
        entry="${remaining%%:*}"
        remaining="${remaining#*:}"
        [ "$entry" = "$remove" ] && continue
        new_path="${new_path:+$new_path:}$entry"
    done

    PATH="$new_path"
}
