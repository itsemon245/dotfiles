#!/usr/bin/env bash

set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
TARGET_DIR="${HOME:?HOME is required}"
INSTALLIGNORE="$REPO_ROOT/.installignore"
RUN_TIMESTAMP="$(date +%Y%m%d%H%M%S)"
BACKUP_ROOT="${DOTFILES_BACKUP_ROOT:-$TARGET_DIR/.local/state/dotfiles/backups/$RUN_TIMESTAMP}"
CONFLICT_POLICY=""

DRY_RUN=false
ADOPT=false
PACKAGES=()
EXCEPT_PACKAGES=()

if [[ -f "$REPO_ROOT/colors.sh" ]]; then
    # shellcheck source=/dev/null
    source "$REPO_ROOT/colors.sh"
else
    RED=$'\033[0;31m'
    GREEN=$'\033[0;32m'
    YELLOW=$'\033[0;33m'
    CYAN=$'\033[0;36m'
    NC=$'\033[0m'
fi

usage() {
    cat <<'EOF'
Usage: ./stow.sh [OPTIONS]

Options:
  --dry-run              Show what would happen without changing files.
  --packages LIST        Stow only comma-separated packages.
  --except LIST          Exclude comma-separated packages.
  --adopt                Pass --adopt to GNU Stow.
  -h, --help             Show this help.

Conflict prompt:
  Y/y or Enter           Back up this conflict only.
  N/n                    Skip this package.
  D/d                    Delete this and later conflicts for this run.
  B/b                    Back up this and later conflicts for this run.
EOF
}

split_csv() {
    local value="$1"
    local item
    local old_ifs="$IFS"

    IFS=','
    for item in $value; do
        item="${item#"${item%%[![:space:]]*}"}"
        item="${item%"${item##*[![:space:]]}"}"
        [[ -n "$item" ]] && printf '%s\n' "$item"
    done
    IFS="$old_ifs"
}

contains_item() {
    local needle="$1"
    shift
    local item

    for item in "$@"; do
        [[ "$item" == "$needle" ]] && return 0
    done

    return 1
}

is_ignored_package() {
    local package="$1"
    local line

    [[ -f "$INSTALLIGNORE" ]] || return 1

    while IFS= read -r line || [[ -n "$line" ]]; do
        line="${line%%#*}"
        line="${line#"${line%%[![:space:]]*}"}"
        line="${line%"${line##*[![:space:]]}"}"
        [[ -z "$line" ]] && continue
        [[ "$line" == "$package" ]] && return 0
    done < "$INSTALLIGNORE"

    return 1
}

list_packages() {
    local package

    if ((${#PACKAGES[@]} > 0)); then
        printf '%s\n' "${PACKAGES[@]}"
        return
    fi

    find "$REPO_ROOT" -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort | while IFS= read -r package; do
        is_ignored_package "$package" && continue
        printf '%s\n' "$package"
    done
}

stow_args() {
    local args=(--dir="$REPO_ROOT" --target="$TARGET_DIR")

    if [[ "$DRY_RUN" == true ]]; then
        args=(-n -v "${args[@]}")
    fi

    if [[ "$ADOPT" == true ]]; then
        args=(--adopt "${args[@]}")
    fi

    printf '%s\0' "${args[@]}"
}

parse_conflicts() {
    sed -n 's/^  \* .*: //p'
}

next_backup_path() {
    local relative_path="$1"
    local candidate="$BACKUP_ROOT/$relative_path"
    local index=1

    while [[ -e "$candidate" || -L "$candidate" ]]; do
        candidate="$BACKUP_ROOT/$relative_path.$index"
        index=$((index + 1))
    done

    printf '%s\n' "$candidate"
}

backup_target() {
    local target="$1"
    local relative_path="${target#"$TARGET_DIR"/}"
    local destination

    if [[ "$relative_path" == "$target" ]]; then
        relative_path="$(basename -- "$target")"
    fi

    destination="$(next_backup_path "$relative_path")"
    mkdir -p -- "$(dirname -- "$destination")"
    mv -- "$target" "$destination"
    printf '%s\n' "$destination"
}

delete_target() {
    local target="$1"

    rm -rf -- "$target"
}

prompt_conflict_action() {
    local target="$1"
    local reply

    case "$CONFLICT_POLICY" in
        backup|delete)
            printf '%s\n' "$CONFLICT_POLICY"
            return 0
            ;;
    esac

    printf '%bConflict:%b %s\n' "$YELLOW" "$NC" "$target" >&2
    printf 'Choose [Y] backup this, [N] skip package, [D] delete all, [B] backup all: ' >&2

    if ! IFS= read -r reply; then
        printf '\n%bNo input available; skipping package.%b\n' "$YELLOW" "$NC" >&2
        printf 'skip\n'
        return 0
    fi

    case "$reply" in
        ""|Y|y)
            printf 'backup\n'
            ;;
        N|n)
            printf 'skip\n'
            ;;
        D|d)
            CONFLICT_POLICY="delete"
            printf 'delete\n'
            ;;
        B|b)
            CONFLICT_POLICY="backup"
            printf 'backup\n'
            ;;
        *)
            printf '%bInvalid choice; skipping package.%b\n' "$YELLOW" "$NC" >&2
            printf 'skip\n'
            ;;
    esac
}

resolve_conflicts() {
    local package="$1"
    shift
    local conflict
    local target
    local action
    local backup_path

    for conflict in "$@"; do
        target="$TARGET_DIR/$conflict"

        if [[ ! -e "$target" && ! -L "$target" ]]; then
            continue
        fi

        action="$(prompt_conflict_action "$target")"

        case "$action" in
            backup)
                backup_path="$(backup_target "$target")" || return 1
                printf '%bBacked up%b %s -> %s\n' "$GREEN" "$NC" "$target" "$backup_path"
                ;;
            delete)
                delete_target "$target" || return 1
                printf '%bDeleted%b %s\n' "$YELLOW" "$NC" "$target"
                ;;
            skip)
                printf '%bSkipped%b %s because %s was left unchanged.\n' "$YELLOW" "$NC" "$package" "$target"
                return 2
                ;;
        esac
    done

    return 0
}

run_stow() {
    local package="$1"
    local args=()

    while IFS= read -r -d '' arg; do
        args+=("$arg")
    done < <(stow_args)

    stow "${args[@]}" "$package"
}

stow_package() {
    local package="$1"
    local output
    local status
    local conflicts=()

    if [[ "$DRY_RUN" == true || "$ADOPT" == true ]]; then
        run_stow "$package"
        return $?
    fi

    while true; do
        output="$(stow --dir="$REPO_ROOT" --target="$TARGET_DIR" -n -v "$package" 2>&1)"
        status=$?

        if ((status == 0)); then
            run_stow "$package"
            return $?
        fi

        mapfile -t conflicts < <(printf '%s\n' "$output" | parse_conflicts)

        if ((${#conflicts[@]} == 0)); then
            printf '%s\n' "$output" >&2
            return "$status"
        fi

        resolve_conflicts "$package" "${conflicts[@]}"
        status=$?

        case "$status" in
            0)
                continue
                ;;
            2)
                return 0
                ;;
            *)
                return "$status"
                ;;
        esac
    done
}

while (($# > 0)); do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            ;;
        --packages)
            shift
            [[ $# -gt 0 ]] || { printf '%b--packages requires a value%b\n' "$RED" "$NC" >&2; exit 1; }
            while IFS= read -r package; do
                PACKAGES+=("$package")
            done < <(split_csv "$1")
            ;;
        --packages=*)
            while IFS= read -r package; do
                PACKAGES+=("$package")
            done < <(split_csv "${1#--packages=}")
            ;;
        --except)
            shift
            [[ $# -gt 0 ]] || { printf '%b--except requires a value%b\n' "$RED" "$NC" >&2; exit 1; }
            while IFS= read -r package; do
                EXCEPT_PACKAGES+=("$package")
            done < <(split_csv "$1")
            ;;
        --except=*)
            while IFS= read -r package; do
                EXCEPT_PACKAGES+=("$package")
            done < <(split_csv "${1#--except=}")
            ;;
        --adopt)
            ADOPT=true
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf '%bUnknown option:%b %s\n' "$RED" "$NC" "$1" >&2
            usage >&2
            exit 1
            ;;
    esac
    shift
done

if ! command -v stow >/dev/null 2>&1; then
    printf '%bError:%b GNU Stow is required.\n' "$RED" "$NC" >&2
    exit 1
fi

mapfile -t SELECTED_PACKAGES < <(list_packages)
FILTERED_PACKAGES=()

for package in "${SELECTED_PACKAGES[@]}"; do
    [[ -d "$REPO_ROOT/$package" ]] || continue
    is_ignored_package "$package" && continue
    contains_item "$package" "${EXCEPT_PACKAGES[@]}" && continue
    FILTERED_PACKAGES+=("$package")
done

if ((${#FILTERED_PACKAGES[@]} == 0)); then
    printf '%bNo packages selected.%b\n' "$YELLOW" "$NC"
    exit 0
fi

printf '%bStowing %d package(s) into %s%b\n' "$CYAN" "${#FILTERED_PACKAGES[@]}" "$TARGET_DIR" "$NC"

failed=()

for package in "${FILTERED_PACKAGES[@]}"; do
    printf '%b==>%b %s\n' "$CYAN" "$NC" "$package"
    if stow_package "$package"; then
        printf '%bOK%b %s\n' "$GREEN" "$NC" "$package"
    else
        printf '%bFAILED%b %s\n' "$RED" "$NC" "$package" >&2
        failed+=("$package")
    fi
done

if ((${#failed[@]} > 0)); then
    printf '%bFailed packages:%b %s\n' "$RED" "$NC" "${failed[*]}" >&2
    exit 1
fi

printf '%bDotfiles stow complete.%b\n' "$GREEN" "$NC"
