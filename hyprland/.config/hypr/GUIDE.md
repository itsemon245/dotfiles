# Maintaining the Hyprland Lua configuration

This directory is a candidate configuration. It is intentionally separate from
the active legacy `~/.config/hypr` configuration, so editing or validating it
cannot interrupt the current desktop session.

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
fallback. Add a local profile only after checking `hyprctl monitors all`; prefer
a `desc:` selector rather than a connector such as `DP-2`.

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

## External tools during migration

The maintained desktop tools detect `~/.config/hypr/hyprland.lua`. While it is
absent they issue legacy `hyprctl` commands; after activation they use Lua
evaluation for monitor changes, window moves and focus, and readability mode.
This keeps `Super + Shift + M` (`rofi-monitor`) useful on either side of the
manual cutover. `wally` regenerates colours and reloads Hyprland in both modes.

## Checks and activation

Before a manual activation:

```sh
find . -path './wallust/*' -prune -o -name '*.lua' -print0 | xargs -0 -r -n1 luac -p
lua-language-server --check=. --check_format=pretty --checklevel=Information
```

After moving this candidate into the live Hyprland location, keep
`hyprland.rescue.lua` beside it. From a TTY, launch it with:

```sh
Hyprland --config ~/.config/hypr/hyprland.rescue.lua
```

Only remove the legacy configuration after the Lua configuration has been
tested on the intended display and on the fallback path.
