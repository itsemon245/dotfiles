# 📝 Tmux Cheatsheet (Prefix = Ctrl + Space)

## Table of Contents

- [Keys](#keys)  
- [Handy tmux Commands](#handy-tmux-commands)  
- [Window Management](#window-management)
- [Session Management](#session-management)
- [Pane Management](#pane-management)  
- [Navigation & Modes](#navigation--modes)  
- [Plugin Manager (TPM) Shortcuts](#plugin-manager-tpm-shortcuts)  
- [Plugin-Specific Useful Shortcuts](#plugin-specific-useful-shortcuts)  

---

## Keys 
### Prefix 
`Ctrl + Space`
- If the prefix has a `*` at the end it means you have to hold it down while pressing the other keys
- If no `*` that means press prefix then release then press other keys
  - `prefix` => press and release then press next keys
  - `prefix*` => press and hold while pressing the next keys

### Other modifier keys
- `C-` means Control(in both mac and other os)
- `Alt-` means Alt and (options in mac)

### Differnce between cases
- Capital letter(`A`, `B`, `C`) means you have to press shift with the letter
- Small letter means just pressing the letter

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

## Window Management
| Shortcut              | Action                                              |
|-----------------------|-----------------------------------------------------|
| `prefix + c`          | Create a new window                                 |
| `prefix + F`          | Create new window at current pane’s path            |
| `prefix + Space`      | Switch to last window                               |
| `prefix + Ctrl+Space` | Switch to last window (same as `prefix + Space`)    |
| `prefix + &`          | Kill the current window                             |
| `prefix + x`          | Kill the current pane                               |

---

## Session Management
| Shortcut     | Action                                                                                                   |
|--------------|----------------------------------------------------------------------------------------------------------|
| `prefix + C-s` | Save the current sessions (*be careful as this will override your existing saves*) |
| `prefix + C-r` | Restore previously saved sessions (*it is common to restore sessions if you can't find them*) |
| `prefix + d` | Detach the session (will keep running in background)                                                     |
| `prefix + s` | This lists all sessions where you can do the following:<br>- Navigate using arrow keys or `k`/`j`<br>- Press `Enter` or session number to enter the session<br>- Press `x` to delete selected session<br> - Press `Esc` to go back |

---

## Pane Management

| Shortcut           | Action                                      |
|--------------------|---------------------------------------------|
| `prefix + -`       | Split pane vertically (down)                 |
| `prefix + \`       | Split pane horizontally (right)              |
| `prefix* + l`  | Clear the terminal (*\* hold prefix while pressing `l`*)                |
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

## Plugin Manager (TPM) Shortcuts

| Shortcut           | Action                         |
|--------------------|-------------------------------|
| `prefix + I`       | Install plugins                |
| `prefix + U`       | Update plugins                 |
| `prefix + Alt+u`   | Clean plugins (remove unused)  |

---

## Plugin-Specific Useful Shortcuts

| Shortcut             | Action                                      |
|----------------------|---------------------------------------------|
| `prefix + t`         | Show time (usually from tmux-net-speed or custom binding) |
| `prefix + Ctrl + s`  | Save tmux session (tmux-resurrect / continuum)       |
| `prefix + Ctrl + r`  | Restore tmux session (tmux-resurrect / continuum)    |
| `prefix + y`         | Copy to system clipboard (tmux-yank)                  |
| `prefix + p`         | Search and paste from copycat history (tmux-copycat)  |
| `prefix + Ctrl + p`  | Toggle prefix highlight (tmux-prefix-highlight)       |

---


*Prefix means your configured prefix key: Ctrl + Space.*
