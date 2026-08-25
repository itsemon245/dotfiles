---@param _settings Dotfiles.Settings
---@return nil
return function(_settings)
  ---@type HL.ConfigOpt
  local config = {
    input = {
      kb_layout = "us",
      kb_variant = "",
      kb_model = "",
      kb_options = "",
      kb_rules = "",
      numlock_by_default = false,
      follow_mouse = 1,
      mouse_refocus = false,
      touchpad = { natural_scroll = true },
    },
  }

  hl.config(config)
  hl.device({ name = "epic-mouse-v1", sensitivity = -0.5 })
end
