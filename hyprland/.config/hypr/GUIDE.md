# Maintaining the Hyprland Lua configuration

This is the active Hyprland configuration. Changes take effect after
`hyprctl reload` unless the module's setting requires a session restart.

## Start here

`hyprland.lua` is the composition root. It loads the shared type declarations,
then `settings`, then each module in its explicit order. A module returns one
function which receives the typed `Dotfiles.Settings` table. That keeps module
dependencies visible and avoids hidden global state.

```
hyprland.lua
  ├── lua/settings.lua        shared data: apps, commands, modifier
  ├── lua/modules/*.lua       one concern each: bindings, rules, monitors, ...
  ├── lua/lib/*.lua           logic the modules call (bindings, rules, theme)
  ├── lua/types/*.lua         editor-only type declarations
  └── tests/*.lua             stub-`hl` tests, run with plain `lua`
```

## Shared data

`lua/settings.lua` is the home for stable, shared configuration data: programs,
commands, the main modifier, workspace count, and similar choices. Every command a
binding runs lives in `settings.commands`; `bindings.lua` holds no command strings. It is a Lua
table, so it can hold any normal Lua value, but keep it declarative: values,
not behaviour. Modules consume it to avoid repeating a command or identifier.

`lua/lib/theme.lua` is the same idea for colours. Wallust renders
`wallust/templates/hyprland-theme.lua` to `lua/generated/theme.lua`; the loader
returns that palette when it is valid and a small built-in palette otherwise. The fallback is
important: a missing or broken generated file must not prevent Hyprland from
starting.

## Runtime and machine-specific directories

| Location | Purpose | Git status |
| --- | --- | --- |
| `lua/generated/` | Runtime output, currently Wallust's `theme.lua`. Never edit this by hand. | Ignored |
| `lua/local/` | This computer's private or hardware-specific overrides, such as exact monitor descriptions. | Ignored except examples |

The base monitor module always registers `preferred` mode with automatic
placement first, so an unfamiliar monitor or a new machine has a usable
fallback. A specific mode (such as 180 Hz) is opt-in, per machine:

1. Run `hyprctl monitors all` while connected to the intended display.
2. Copy `lua/local/machine.example.lua` to `lua/local/machine.lua`.
3. Set `output` to the connector name, such as `DP-2`. Use a `desc:` selector
   only when the same monitor should follow it across connectors.

## Modules and helpers

Keep a module focused on one Hyprland concern: input, appearance, rules,
bindings, and so on. If a module needs a contract shared by another module,
place it in `lua/types/modules.lua`; small private types stay beside their
module. The `lua/types` directory is in LuaLS's workspace library, so these are
editor-only declarations rather than runtime imports.

Bindings use the table-based helpers in `lua/lib/bindings.lua`:

```lua
bind({
  keys = mod("RETURN"),
  action = helper.exec(settings.apps.terminal),
  desc = "Open terminal",
})
```

`mod(keys)` adds the configured main modifier. Keep shortcut-local modifiers in
the key string, for example `mod("SHIFT + C")`. The named fields make calls
readable and let LuaLS validate them. The helper puts `desc` on the Hyprland
bind options, which makes it available in `hyprctl binds`. `Super + /` opens a
searchable, self-maintaining Rofi manual generated from these binding specs. It
uses the wider `~/.config/rofi/hypr-keybinds.rasi` theme, derived from the
compact adi1090x applet style; adding a binding automatically adds its key and
description to the manual. Rofi fuzzy-matches and highlights both fields.
`helper.exec(command,
rules?)` is the short readable wrapper for
Hyprland's `exec_cmd` dispatcher; omit `rules` unless an execution rule is
needed.

`action` accepts either an `HL.Dispatcher` or a callback. Prefer a dispatcher
for one native Hyprland action. A callback is useful when one key must compose
several operations:

```lua
bind({
  keys = mod("N"),
  desc = "Notify and launch terminal",
  action = function()
    hl.notification.create({ text = "Opening terminal" })
    hl.exec_cmd(settings.apps.terminal)
  end,
})
```

## External tools

The maintained desktop tools use Lua evaluation for monitor changes, window
moves, focus, and readability mode. This keeps `Super + Shift + M`
(`rofi-monitor`) aligned with the configuration. `wally` regenerates the Lua
theme and reloads Hyprland.

Bindings and bar buttons call tools in `~/.local/bin` by full path
(`~/.local/bin/hypr-logout`). `~/.zprofile` also puts that folder on the login
PATH Hyprland inherits from SDDM, but only from the next login, and a bare name
silently does nothing in a session that started before it. Keep using full paths.

## Session, power and recovery keys

| Keys | Action |
| --- | --- |
| `Super + Shift + R` | Log out (`hypr-logout`, through `hyprshutdown` when installed). Deliberately not `Super + R`, which sits next to `Super + T`. |
| Waybar power button | `power-menu`: lock, suspend, hibernate, log out, reboot, shut down. |
| `Super + Shift + B` | Restart Waybar (`barr`). |
| `Super + Ctrl + Escape` | Kill a stuck rofi layer and restart IBus. IBus runs as the Wayland input method for Bangla input and takes the keyboard grab whenever rofi opens; if that handover breaks, rofi stops taking keys. Compositor bindings are matched before keys reach the input method, so this still works. Last resort: `Ctrl + Alt + F3`, log in, `pkill -x rofi; ibus restart`. |

## Window rules

`modules/rules.lua` is data; the logic is in `lib/rules.lua`, like
`lib/bindings.lua` for bindings. To float an app centred, add its class to a
group in the `floating` table:

```lua
local floating = {
  large  = { size = { 800, 600 }, classes = { "xdg-desktop-portal-gtk" } },
  medium = { size = { 760, 480 }, classes = { "blueman-manager" } },
  small  = { size = { 500, 400 }, classes = { "floating-sm" },
             windows = { { class = "xdm-app", title = "^Download" } } },
}
```

Group names are only labels; every group states its own `size`, so the size you
read is the size you get.

Find a class with `hyprctl clients` while the window is open. Classes match
exactly (dots and all), so list each variant an app uses. `windows` sizes only
some of an app's windows, matched by title (a regex), such as dialogs. Array
entries also work: `{ name = "medium", classes = { ... } }`.

Order never matters. A class may sit in only one group, so app-wide rules cannot
overlap, and `windows` entries are always applied after every class rule (in
Hyprland the later rule wins), so a dialog's size overrides its app's. Mistakes
(unknown key, bad size, a class in two groups) show a notification and only that
entry is skipped.

`rules.lua` also starts with a rule that ignores maximize requests from every
app (the same rule Hyprland's default config ships). Without it, kitty restores
a remembered "maximized" state on launch and covers the tiled windows until
fullscreen is toggled.

## Checks and recovery

Before reloading a configuration change:

```sh
lua tests/rules_test.lua   # window-rule groups: formats, ordering, mistakes
find . -path './wallust/*' -prune -o -name '*.lua' -print0 | xargs -0 -r -n1 luac -p
lua-language-server --check=. --check_format=pretty --checklevel=Information
Hyprland --verify-config -c ~/.config/hypr/hyprland.lua   # what Hyprland itself would load
```

The language server reads `.luarc.json`, which loads Hyprland's API stubs from
`/usr/share/hypr/stubs`; editor checks without that file report false `hl` warnings.

Keep `hyprland.rescue.lua` beside the main configuration. From a TTY, launch it
with:

```sh
Hyprland --config ~/.config/hypr/hyprland.rescue.lua
```
