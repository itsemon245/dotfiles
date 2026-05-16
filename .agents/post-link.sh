#!/usr/bin/env bash
# Post-link hook: ensures all agent directory symlinks are listed in .installignore
# so stow doesn't treat them as packages.

INSTALLIGNORE="$REPO_DIR/.installignore"

for dir in "${TOOL_DIRS[@]}"; do
    if ! grep -qxF "$dir" "$INSTALLIGNORE" 2>/dev/null; then
        echo "ignore $dir (added to .installignore)"
        run bash -c "echo '$dir' >> '$INSTALLIGNORE'"
    fi
done
