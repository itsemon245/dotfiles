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
  ├── lua/settings.lua
  ├── lua/theme.lua
  └── lua/modules/*.lua
```

## Shared data

`lua/settings.lua` is the home for stable, shared configuration data: programs,
commands, the main modifier, workspace count, and similar choices. It is a Lua
table, so it can hold any normal Lua value, but keep it declarative: values,
not behaviour. Modules consume it to avoid repeating a command or identifier.

`lua/theme.lua` is the same idea for colours. It returns the generated Wallust
palette when it is valid and a small built-in palette otherwise. The fallback is
important: a missing or broken generated file must not prevent Hyprland from
starting.

## Runtime and machine-specific directories

| Location | Purpose | Git status |
| --- | --- | --- |
| `lua/generated/` | Runtime output, currently Wallust's `theme.lua`. Never edit this by hand. | Ignored |
| `lua/local/` | This computer's private or hardware-specific overrides, such as exact monitor descriptions. | Ignored except examples |
| `lua/profiles/` | Tracked, reusable opt-in presets, for example a laptop-only or docked display layout. Nothing here is loaded automatically. | Tracked |

The base monitor module always registers `preferred` mode with automatic
placement first. Therefore an unfamiliar monitor or a new machine has a usable
fallback. Add a local profile only after checking `hyprctl monitors all`; use a
connector such as `DP-2` for a machine-local profile, or a `desc:` selector
when the same monitor needs to follow a different connector.

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

## Checks and recovery

Before reloading a configuration change:

```sh
find . -path './wallust/*' -prune -o -name '*.lua' -print0 | xargs -0 -r -n1 luac -p
lua-language-server --check=. --check_format=pretty --checklevel=Information
```

Keep `hyprland.rescue.lua` beside the main configuration. From a TTY, launch it
with:

```sh
Hyprland --config ~/.config/hypr/hyprland.rescue.lua
```
