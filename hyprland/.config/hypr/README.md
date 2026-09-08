# Hyprland Lua configuration

This is the active Hyprland configuration. `hyprland.lua` is the entry point.

Read [GUIDE.md](GUIDE.md) for the directory layout, shared settings and theme
tables, module conventions, binding manual, and safe maintenance workflow.

## Static analysis

- Lua Language Server reads `.luarc.json` and Hyprland's installed API stubs from `/usr/share/hypr/stubs`.
- `luac -p` checks Lua syntax.
- Run `lua-language-server --check=. --check_format=pretty --checklevel=Information` from this directory for diagnostics.

## Safe monitor behaviour

`lua/modules/monitors.lua` always applies a `preferred`/`auto` fallback for unknown displays. The current 180 Hz profile is deliberately opt-in:

1. Run `hyprctl monitors all` while connected to the intended display.
2. Copy `lua/local/machine.example.lua` to `lua/local/machine.lua`.
3. Set `output` to the connector name, such as `DP-2`. Use a `desc:` selector
   only when you want the same profile to follow a monitor across connectors.

`lua/local/machine.lua` is ignored by Git, so it can vary per computer without making the shared configuration unsafe.

## Theme generation

Wallust renders `wallust/templates/hyprland-theme.lua` to
`lua/generated/theme.lua`. The configuration uses a built-in neutral palette
whenever the generated file is absent or invalid.

## Desktop tools

The maintained desktop tools use Hyprland's Lua evaluation interface for
monitor changes, window moves, focus, and readability mode.

## Rescue profile

If a tested switch fails, launch the adjacent `hyprland.rescue.lua` from a TTY with:

```sh
Hyprland --config ~/.config/hypr/hyprland.rescue.lua
```
