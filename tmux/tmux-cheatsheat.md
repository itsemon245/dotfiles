# 📝 Tmux Cheatsheet (Prefix = Ctrl + Space)

## Prefix key  
`Ctrl + Space`

---

## Session & Window Management

| Shortcut              | Action                                 |
|----------------------|---------------------------------------|
| `prefix + Space`      | Switch to last window                  |
| `prefix + &`          | Kill the current window                |
| `prefix + x`          | Kill the current pane                  |
| `prefix + F`          | Create new window at current pane’s path |
| `prefix + D`          | Run shell command: `t ~/dotfiles` (custom) |
| `prefix + Ctrl+Space` | Switch to last window (same as prefix + Space) |
| `Alt + H (M-H)`       | Previous window                       |
| `Alt + L (M-L)`       | Next window                           |

---

## Pane Management

| Shortcut           | Action                                      |
|--------------------|---------------------------------------------|
| `prefix + -`       | Split pane vertically (down)                 |
| `prefix + \`       | Split pane horizontally (right)              |
| `prefix + Ctrl+k`  | Clear the pane (runs `clear`)                 |
| `Ctrl + h`         | If inside Vim: send Ctrl+h; else move to left pane |
| `Ctrl + j`         | If inside Vim: send Ctrl+j; else move to pane below  |
| `Ctrl + l`         | If inside Vim: send Ctrl+l; else move to right pane  |

---

## Navigation & Modes

| Shortcut          | Action                               |
|-------------------|-------------------------------------|
| `prefix + Space`  | Last window                         |
| Mouse support     | Click to select panes/windows       |
| Vi-style copy mode| `prefix + [` enters copy mode (default) |

---

## Handy tmux Commands

| Command                              | Description                         |
|------------------------------------|-----------------------------------|
| `tmux ls`                          | List all tmux sessions             |
| `tmux attach` or `tmux a`          | Attach to last session              |
| `tmux attach -t <session-name>`    | Attach to specific session          |
| `tmux kill-server`                  | Kill all tmux sessions & server     |
| `tmux kill-session -t <session-name>` | Kill a specific session            |
| `tmux kill-window -t <window>`      | Kill a specific window              |
| `tmux kill-pane -t <pane>`          | Kill a specific pane                |
| `tmux new -s <name>`                | Create new session with name         |
| `tmux source-file ~/.tmux.conf`     | Reload tmux config                  |

---

## Plugin Manager (TPM) Shortcuts

| Shortcut           | Action                    |
|--------------------|--------------------------|
| `prefix + I`       | Install plugins            |
| `prefix + U`       | Update plugins             |
| `prefix + Alt+u`   | Clean plugins (remove unused) |

---

*Prefix means your configured prefix key: Ctrl + Space.*

