# Hyprland Lua candidate

This is an isolated migration candidate. Nothing in this directory is loaded by the active legacy configuration.

Read [GUIDE.md](GUIDE.md) for the directory layout, shared settings and theme
tables, module conventions, binding manual, and safe maintenance workflow.

## Static analysis

- Lua Language Server reads `.luarc.json` and Hyprland's installed API stubs from `/usr/share/hypr/stubs`.
- `luac -p` checks Lua syntax.
- Run `lua-language-server --check=. --check_format=pretty --checklevel=Information` from this directory for diagnostics.

## Safe monitor behavior

`lua/modules/monitors.lua` always applies a `preferred`/`auto` fallback for unknown displays. The current 180 Hz profile is deliberately opt-in:

1. Run `hyprctl monitors all` while connected to the intended display.
2. Copy `lua/local/machine.example.lua` to `lua/local/machine.lua`.
3. Replace the placeholder with the monitor's `desc:` selector.

`lua/local/machine.lua` is ignored by Git, so it can vary per computer without making the shared configuration unsafe.

## Theme handoff

After testing, register `wallust/hyprland-theme.lua.j2` as a Wallust template targeting:

```toml
hyprland_lua = { template = "hyprland-theme.lua", target = "~/.config/hypr/lua/generated/theme.lua" }
```

The candidate uses a built-in neutral palette whenever that generated file is absent or invalid.

## Runtime-tool handoff

The maintained desktop tools are now dual-compatible: they retain legacy
`hyprctl` commands until `~/.config/hypr/hyprland.lua` exists, then use the Lua
equivalents. See [GUIDE.md](GUIDE.md#external-tools-during-migration) for the
covered commands and cutover behaviour.

## Rescue profile

If a tested switch fails, launch the adjacent `hyprland.rescue.lua` from a TTY with:

```sh
Hyprland --config ~/.config/hypr/hyprland.rescue.lua
```
