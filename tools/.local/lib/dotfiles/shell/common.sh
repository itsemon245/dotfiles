# Common startup-safe helpers. This file intentionally has no source-time output.

_dotfiles_shell_common_source="${BASH_SOURCE[0]-}"
if [ -z "$_dotfiles_shell_common_source" ] && [ -n "${ZSH_VERSION:-}" ]; then
    _dotfiles_shell_common_source="${(%):-%N}"
fi
_dotfiles_shell_common_dir="$(CDPATH= cd -- "$(dirname -- "$_dotfiles_shell_common_source")" && pwd)"

# shellcheck source=path.sh
. "$_dotfiles_shell_common_dir/path.sh"
# shellcheck source=source.sh
. "$_dotfiles_shell_common_dir/source.sh"
# shellcheck source=env.sh
. "$_dotfiles_shell_common_dir/env.sh"

unset _dotfiles_shell_common_source _dotfiles_shell_common_dir
