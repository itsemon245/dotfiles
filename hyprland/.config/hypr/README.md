# Hyprland Lua configuration

A Lua configuration for Hyprland 0.57+ (`hyprland.lua` is the entry point). It is
split into small modules (bindings, window rules, monitors, appearance, startup)
that read shared values from `lua/settings.lua`, so a command or app name is
written once. Colours come from the current wallpaper through Wallust, with a
built-in palette if the generated theme is missing.

It is part of the `hyprland` stow package in the dotfiles repo, together with
Waybar, Rofi, Wallust and the other desktop configs; the tools it calls (`wally`,
`power-menu`, `hypr-startup`, ...) come from the `tools` package.

## Quickstart

```sh
cd ~/dotfiles && stow hyprland tools zsh          # links ~/.config/hypr and the tools
cp -n ~/.config/hypr/lua/local/machine.example.lua ~/.config/hypr/lua/local/machine.lua   # -n: keeps an existing one
$EDITOR ~/.config/hypr/lua/local/machine.lua      # optional: your monitor's mode and rate
Hyprland --verify-config -c ~/.config/hypr/hyprland.lua
```

Then log in to Hyprland (or run `hyprctl reload` in a running session). Without a
`machine.lua`, every monitor gets its preferred mode, so this step is optional.
`zsh` provides `~/.zprofile`, which puts the tools on the session PATH.

## Keys to start with

| Keys | Action |
| --- | --- |
| `Super + /` | Searchable list of every binding |
| `Super + T` | Terminal (kitty) |
| `Super + Space` | App launcher |
| `Super + Q` | Close window |
| `Super + F` | Fullscreen |
| `Super + V` | Clipboard history |
| `Super + W` | Pick a wallpaper (and regenerate the colours) |
| `Super + S` | Show/hide the scratch workspace |
| `Super + Shift + R` | Log out |

## Where to change things

| To change | Edit |
| --- | --- |
| An app or command a key runs | `lua/settings.lua` (`apps`, `commands`) |
| A key binding | `lua/modules/bindings.lua` |
| Which apps float, and their size | the `floating` table in `lua/modules/rules.lua` |
| Monitor mode, rate, position | `lua/local/machine.lua` (this machine only, not committed) |
| Gaps, borders, blur, opacity | `lua/modules/appearance.lua` |
| Apps started at login | `hypr-startup` in the `tools` package |

[GUIDE.md](GUIDE.md) explains the layout, the conventions behind it, and the
checks to run before reloading.

## If it breaks

From a TTY (`Ctrl + Alt + F3`), start the minimal rescue config:

```sh
Hyprland --config ~/.config/hypr/hyprland.rescue.lua
```
