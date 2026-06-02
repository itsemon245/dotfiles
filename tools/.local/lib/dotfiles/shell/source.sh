# Startup-safe sourcing helpers for bash and zsh.

source_if_exists() {
    local file="${1:-}"

    [ -r "$file" ] || return 0
    # shellcheck source=/dev/null
    . "$file"
}

source_dir_if_exists() {
    local dir="${1:-}"
    local find_dir
    local file

    [ -d "$dir" ] || return 0
    find_dir="$dir/"

    while IFS= read -r file; do
        [ -r "$file" ] || continue
        # shellcheck source=/dev/null
        . "$file"
    done <<EOF
$(find "$find_dir" -maxdepth 1 -type f \( -name '*.sh' -o -name '*.zsh' \) 2>/dev/null | sort)
EOF
}
