---@param _settings Dotfiles.Settings
---@return nil
return function(_settings)
  hl.window_rule({
    name = "xdm-main-window",
    match = { class = "xdm-app" },
    float = true,
    size = { 800, 600 },
    center = true,
  })

  hl.window_rule({
    name = "xdm-dialog",
    match = { class = "xdm-app", title = "^(?:[0-9]+%|Download|Confirm|Progress).*" },
    float = true,
    size = { 500, 400 },
    center = true,
  })

  hl.window_rule({
    name = "floating-small",
    match = { class = "floating-sm|floating-small" },
    float = true,
    size = { 500, 400 },
    center = true,
  })

  hl.window_rule({
    name = "floating-large",
    match = { class = "floating-lg|floating-large|xdg-desktop-portal-gtk" },
    float = true,
    size = { 800, 600 },
    center = true,
  })

  hl.window_rule({ name = "waydroid-fullscreen", match = { class = "Waydroid" }, fullscreen = true })
  hl.window_rule({ name = "overwatch-immediate", match = { title = "Overwatch" }, immediate = true })
  hl.layer_rule({
    name = "glassy-blur",
    match = { namespace = "rofi|waybar|notifications|logout_dialog|wlogout|tooltip" },
    blur = true,
    ignore_alpha = 0.005,
  })
end
