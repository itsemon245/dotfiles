_dotfiles_shell_helpers="${DOTFILES_SHELL_HELPERS:-$HOME/.local/lib/dotfiles/shell/common.sh}"
if [[ -r "$_dotfiles_shell_helpers" ]]; then
    source "$_dotfiles_shell_helpers"
fi
unset _dotfiles_shell_helpers

if ! command -v source_if_exists >/dev/null 2>&1; then
    source_if_exists() {
        [[ -r "$1" ]] && source "$1"
    }
fi

if ! command -v source_dir_if_exists >/dev/null 2>&1; then
    source_dir_if_exists() {
        local dir="${1:-}"
        local find_dir
        local file

        [[ -d "$dir" ]] || return 0
        find_dir="$dir/"
        while IFS= read -r file; do
            [[ -r "$file" ]] && source "$file"
        done <<EOF
$(find "$find_dir" -maxdepth 1 -type f \( -name '*.sh' -o -name '*.zsh' \) 2>/dev/null | sort)
EOF
    }
fi

if ! command -v path_prepend >/dev/null 2>&1; then
    path_contains() {
        case ":${PATH:-}:" in
            *":$1:"*) return 0 ;;
            *) return 1 ;;
        esac
    }

    path_prepend() {
        [[ -n "${1:-}" ]] || return 0
        path_contains "$1" && return 0
        PATH="$1${PATH:+:$PATH}"
    }

    path_append() {
        [[ -n "${1:-}" ]] || return 0
        path_contains "$1" && return 0
        PATH="${PATH:+$PATH:}$1"
    }
fi

#Oh-my-zsh things
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="robbyrussell"
plugins=(git zsh-autosuggestions zsh-syntax-highlighting fzf)
source_if_exists "$ZSH/oh-my-zsh.sh"

#Source helpers from utils
source_if_exists "$HOME/zsh_utils/helpers.sh"

#Source Scripts
source_dir_if_exists "$HOME/aliases"
source_if_exists "$HOME/exports.sh"
source_if_exists "$HOME/ssh-agent.sh"

path_prepend "/opt/homebrew/opt/libpq/bin"

# Added by LM Studio CLI (lms)
path_append "$HOME/.lmstudio/bin"
# End of LM Studio CLI section


# Added by Antigravity
path_prepend "$HOME/.antigravity/antigravity/bin"
