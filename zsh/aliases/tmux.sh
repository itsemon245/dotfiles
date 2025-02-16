#Starts a new tmux session and close it to attach a saved session
function mux {
  local session_name="$1"

    if [ -z "$session_name" ]; then
        echo "Usage: tmux_restore <session_name>"
        return 1
    fi

    # Check if the session exists
    if tmux has-session -t "$session_name" 2>/dev/null; then
        tmux attach-session -t "$session_name"
        return 0
    fi

    # Create a new session in detached mode
    tmux new-session -d -s temp_restore_session

    # Send Ctrl+R to restore saved sessions
    tmux send-keys -t temp_restore_session C-r

    # Wait a moment to allow the restore process to complete
    sleep 2

    # Check if the requested session is now available
    if tmux has-session -t "$session_name" 2>/dev/null; then
        tmux kill-session -t temp_restore_session
        tmux attach-session -t "$session_name"
    else
        tmux kill-session -t temp_restore_session
        echo "No tmux session found"
    fi
}

alias ta='tmux a -t'
