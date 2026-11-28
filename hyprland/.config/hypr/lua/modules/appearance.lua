local theme = require("lua.lib.theme")

---@param _settings Dotfiles.Settings
---@return nil
return function(_settings)
  ---@type HL.ConfigOpt
  local config = {
    general = {
      gaps_in = 4,
      gaps_out = 8,
      border_size = 1,
      allow_tearing = false,
      layout = "master",
      col = {
        active_border = { colors = { theme.primary, theme.secondary }, angle = 45 },
        inactive_border = theme.primary_dim,
      },
    },
    decoration = {
      rounding = 10,
      active_opacity = 0.75,
      inactive_opacity = 0.5,
      blur = {
        enabled = true,
        size = 2,
        passes = 4,
        vibrancy = 0.5,
        popups = true,
        ignore_opacity = true,
      },
    },
    misc = {
      -- A visible compositor fallback is safer than a blank desktop when no wallpaper backend is available.
      force_default_wallpaper = -1,
      disable_hyprland_logo = false,
      disable_splash_rendering = false,
      background_color = theme.background,
    },
    render = {
      -- Off: fullscreen HDR content (Chrome) would switch the monitor into HDR. On this
      -- entry-level HDR panel that means a black flash and grainy, washed-out blacks,
      -- even with bitdepth = 10, so fullscreen stays SDR.
      cm_auto_hdr = 0,
    },
    debug = {
      disable_logs = false,
      overlay = false,
      damage_blink = false,
    },
  }

  hl.config(config)
end
