#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/system/wireplumber.conf.d"
TARGET_DIR="/etc/wireplumber/wireplumber.conf.d"
DRY_RUN=false

usage() {
    cat <<'EOF'
Usage: ./wireplumber/install-system-config.sh [OPTIONS]

Install this repository's WirePlumber device-priority rules for every user.

Options:
  --dry-run       Show the files that would be installed.
  -h, --help      Show this help.
EOF
}

while (($# > 0)); do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'Unknown option: %s\n' "$1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

if [[ ! -d "$SOURCE_DIR" ]]; then
    printf 'WirePlumber source directory is missing: %s\n' "$SOURCE_DIR" >&2
    exit 1
fi

config_files=()
while IFS= read -r -d '' config_file; do
    config_files+=("$config_file")
done < <(find "$SOURCE_DIR" -maxdepth 1 -type f -name '*.conf' -print0 | sort -z)

if ((${#config_files[@]} == 0)); then
    printf 'No WirePlumber configuration fragments found in %s\n' "$SOURCE_DIR" >&2
    exit 1
fi

if [[ "$DRY_RUN" == true ]]; then
    printf 'Would create %s\n' "$TARGET_DIR"
    for config_file in "${config_files[@]}"; do
        printf 'Would install %s -> %s/%s\n' "$config_file" "$TARGET_DIR" "$(basename -- "$config_file")"
    done
    exit 0
fi

sudo install -d -m 0755 "$TARGET_DIR"
for config_file in "${config_files[@]}"; do
    sudo install -m 0644 "$config_file" "$TARGET_DIR/$(basename -- "$config_file")"
done

printf 'Installed %d WirePlumber configuration fragment(s) in %s\n' "${#config_files[@]}" "$TARGET_DIR"
