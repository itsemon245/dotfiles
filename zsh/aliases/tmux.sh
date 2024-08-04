#Starts a new tmux session and close it to attach a saved session
function mux {
  if [[ $# -gt 0 ]]; then
    pgrep -vx tmux > /dev/null && \
      tmux new -d -s delete-me && \
      tmux run-shell ~/.config/tmux/plugins/tmux-resurrect/scripts/restore.sh && \
      tmux kill-session -t delete-me && \
      tmux attach -t $1 || tmux attach -t $1
  else
    pgrep -vx tmux > /dev/null && \
      tmux new -d -s delete-me && \
      tmux run-shell ~/.config/tmux/plugins/tmux-resurrect/scripts/restore.sh && \
      tmux kill-session -t delete-me && \
      tmux attach || tmux attach
      fi
}

alias ta='tmux a -t'
