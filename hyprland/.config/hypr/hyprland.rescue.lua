-- Minimal recovery profile. Start from a TTY with:
-- Hyprland --config ~/.config/hypr/hyprland.rescue.lua

hl.monitor({ output = "", mode = "preferred", position = "auto", scale = 1 })

---@type HL.ConfigOpt
local config = {
  general = { gaps_in = 4, gaps_out = 8, border_size = 1, layout = "master" },
  input = { kb_layout = "us" },
  misc = { force_default_wallpaper = -1 },
}

hl.config(config)
hl.bind("SUPER + Q", hl.dsp.exec_cmd("kitty"), { desc = "Open terminal" })
hl.bind("SUPER + R", hl.dsp.exec_cmd("rofi -show drun"), { desc = "Open app launcher" })
hl.bind("SUPER + SHIFT + R", hl.dsp.exec_cmd("hyprctl reload"), { desc = "Reload configuration" })
hl.bind("SUPER + SHIFT + X", hl.dsp.exit(), { desc = "Exit Hyprland" })
