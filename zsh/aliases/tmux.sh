#Starts a new tmux session and close it to attach a saved session
function mux {
  if [[ $# -gt 0 ]]; then
    if ! pgrep -vx tmux > /dev/null; then
      tmux new -d -s delete-me
      tmux run-shell ~/.tmux/plugins/tmux-resurrect/scripts/restore.sh
      tmux kill-session -t delete-me
    fi
    tmux attach -t "$1" || tmux new -s "$1"
  else
    if ! pgrep -vx tmux > /dev/null; then
      tmux new -d -s delete-me
      tmux run-shell ~/.tmux/plugins/tmux-resurrect/scripts/restore.sh
      tmux kill-session -t delete-me
    fi
    tmux attach || tmux new -s default
  fi
}

alias ta='tmux a -t'
