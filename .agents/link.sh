#!/usr/bin/env bash
# Symlinks coding agent directories and instruction files to this single source of truth.
#
# Usage:
#   .agents/link.sh                     # Link all defaults
#   .agents/link.sh --dir .windsurf     # Add a new directory symlink
#   .agents/link.sh --file WINDSURF.md  # Add a new instruction file symlink
#   .agents/link.sh --force             # Overwrite conflicting files during merge
#   .agents/link.sh --dry-run           # Preview changes
#
# Flags can be combined: .agents/link.sh --dir .windsurf --file WINDSURF.md --dry-run
#
# Post-link hook:
#   If .agents/post-link.sh exists it is sourced after all links are created.
#   Available variables in post-link.sh:
#     REPO_DIR              - Absolute path to the repository root
#     SCRIPT_DIR            - Absolute path to .agents/
#     SOURCE                - Relative symlink target for directories (default: ".agents")
#     CANONICAL_INSTRUCTIONS - Relative symlink target for files (default: "AGENTS.md")
#     TOOL_DIRS[@]          - Array of all directory names that were processed
#     INSTRUCTION_FILES[@]  - Array of all instruction file names that were processed
#     dry_run               - 1 if --dry-run was passed, 0 otherwise
#     force                 - 1 if --force was passed, 0 otherwise
#     run <cmd...>          - Helper function: executes cmd unless dry_run=1
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
SOURCE=".agents"
CANONICAL_INSTRUCTIONS="AGENTS.md"

# Agent tool directories that should be symlinks to .agents/
TOOL_DIRS=(
    .claude
    .codex
    .cursor
    .gemini
    .ai
    .opencode
)

# Instruction files that should symlink to the canonical AGENTS.md
INSTRUCTION_FILES=(
    GEMINI.md
    CLAUDE.md
    CURSORRULES
    .cursorrules
)

dry_run=0
force=0
extra_dirs=()
extra_files=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            dry_run=1
            shift
            ;;
        --force)
            force=1
            shift
            ;;
        --dir)
            [[ -z "${2:-}" ]] && { echo "error: --dir requires a value" >&2; exit 1; }
            extra_dirs+=("$2")
            shift 2
            ;;
        --file)
            [[ -z "${2:-}" ]] && { echo "error: --file requires a value" >&2; exit 1; }
            extra_files+=("$2")
            shift 2
            ;;
        -h|--help)
            sed -n '/^# Usage:/,/^[^#]/p' "${BASH_SOURCE[0]}" | grep '^#' | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "error: unknown option: $1" >&2
            echo "Run with --help for usage." >&2
            exit 1
            ;;
    esac
done

TOOL_DIRS+=("${extra_dirs[@]}")
INSTRUCTION_FILES+=("${extra_files[@]}")

run() {
    if [[ "$dry_run" -eq 1 ]]; then
        echo "[dry-run] $*"
    else
        "$@"
    fi
}

# Validate inputs: no slashes, no empty names, no absolute paths
validate_name() {
    local name="$1" kind="$2"
    if [[ -z "$name" || "$name" == */* || "$name" == /* ]]; then
        echo "error: invalid $kind name: '$name' (must be a simple name, no slashes)" >&2
        exit 1
    fi
}

# Find conflicting files between a source dir and the canonical .agents/ dir.
# Returns list of relative paths that exist in both with different content.
find_conflicts() {
    local dir="$1"
    local conflicts=()

    while IFS= read -r -d '' file; do
        local rel="${file#"$dir"/}"
        local target="$SOURCE/$rel"
        if [[ -f "$target" ]] && ! cmp -s "$file" "$target"; then
            conflicts+=("$rel")
        fi
    done < <(find "$dir" -type f -print0)

    printf '%s\n' "${conflicts[@]}"
}

# Merge a directory into .agents/, detecting conflicts
merge_dir() {
    local dir="$1"
    local conflicts

    conflicts="$(find_conflicts "$dir")"

    if [[ -n "$conflicts" && "$force" -eq 0 ]]; then
        echo "conflict: $dir/ has files that differ from $SOURCE/:" >&2
        while IFS= read -r f; do
            echo "  $f" >&2
        done <<< "$conflicts"
        echo "" >&2
        echo "Run with --force to overwrite with $SOURCE/ version, or manually resolve:" >&2
        echo "  diff $dir/<file> $SOURCE/<file>" >&2
        return 1
    fi

    # Copy new files (no-clobber for non-conflicting)
    while IFS= read -r -d '' file; do
        local rel="${file#"$dir"/}"
        local target="$SOURCE/$rel"
        if [[ ! -e "$target" ]]; then
            run mkdir -p "$(dirname "$target")"
            run cp "$file" "$target"
            echo "  adopt $rel"
        fi
    done < <(find "$dir" -type f -print0)

    # If --force, overwrite conflicts with .agents/ version (source of truth wins)
    # The files in the old dir are simply discarded since .agents/ is canonical.
    if [[ -n "$conflicts" && "$force" -eq 1 ]]; then
        echo "  forced: keeping $SOURCE/ versions for conflicting files"
    fi

    run rm -rf "$dir"
}

link_dir() {
    local dir="$1"
    validate_name "$dir" "directory"

    # Already correct — idempotent no-op
    if [[ -L "$dir" ]]; then
        local current
        current="$(readlink "$dir")"
        if [[ "$current" == "$SOURCE" ]]; then
            echo "ok   $dir -> $SOURCE"
            return
        fi
        echo "fix  $dir (was -> $current)"
        run rm "$dir"
    elif [[ -d "$dir" ]]; then
        echo "merge $dir/ -> $SOURCE/"
        if ! merge_dir "$dir"; then
            echo "skip $dir (unresolved conflicts)" >&2
            return 1
        fi
    elif [[ -e "$dir" ]]; then
        echo "rm   $dir (not a directory or symlink, replacing)"
        run rm "$dir"
    fi

    echo "link $dir -> $SOURCE"
    run ln -s "$SOURCE" "$dir"
}

link_file() {
    local file="$1"
    validate_name "$file" "file"

    # Already correct — idempotent no-op
    if [[ -L "$file" ]]; then
        local current
        current="$(readlink "$file")"
        if [[ "$current" == "$CANONICAL_INSTRUCTIONS" ]]; then
            echo "ok   $file -> $CANONICAL_INSTRUCTIONS"
            return
        fi
        echo "fix  $file (was -> $current)"
        run rm "$file"
    elif [[ -f "$file" ]]; then
        if [[ -f "$CANONICAL_INSTRUCTIONS" ]] && ! cmp -s "$file" "$CANONICAL_INSTRUCTIONS"; then
            if [[ "$force" -eq 0 ]]; then
                echo "conflict: $file differs from $CANONICAL_INSTRUCTIONS" >&2
                echo "  Run with --force to discard $file, or manually resolve:" >&2
                echo "  diff $file $CANONICAL_INSTRUCTIONS" >&2
                echo "skip $file (unresolved conflict)" >&2
                return 1
            fi
            echo "  forced: discarding $file in favor of $CANONICAL_INSTRUCTIONS"
        fi
        run rm "$file"
    elif [[ -e "$file" ]]; then
        echo "rm   $file (unexpected type, replacing)"
        run rm "$file"
    fi

    echo "link $file -> $CANONICAL_INSTRUCTIONS"
    run ln -s "$CANONICAL_INSTRUCTIONS" "$file"
}

cd "$REPO_DIR"

# Ensure the source directory exists
if [[ ! -d "$SOURCE" ]]; then
    echo "error: source directory '$REPO_DIR/$SOURCE' does not exist" >&2
    exit 1
fi

# Ensure canonical instructions file exists
if [[ ! -f "$CANONICAL_INSTRUCTIONS" && ! -L "$CANONICAL_INSTRUCTIONS" ]]; then
    echo "error: canonical instructions file '$CANONICAL_INSTRUCTIONS' does not exist" >&2
    exit 1
fi

has_errors=0

for dir in "${TOOL_DIRS[@]}"; do
    link_dir "$dir" || has_errors=1
done

for file in "${INSTRUCTION_FILES[@]}"; do
    link_file "$file" || has_errors=1
done

# Source post-link hook if it exists
if [[ -f "$SCRIPT_DIR/post-link.sh" ]]; then
    echo "running post-link.sh..."
    source "$SCRIPT_DIR/post-link.sh"
fi

if [[ "$has_errors" -eq 1 ]]; then
    echo "done (with conflicts — re-run with --force or resolve manually)"
    exit 1
fi

echo "done"
