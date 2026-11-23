---@param _settings Dotfiles.Settings
---@return nil
return function(_settings)
  -- Apps such as kitty restore a remembered "maximized" state on launch, which
  -- covers the tiled layout until fullscreen is toggled. Tiling decides sizes.
  hl.window_rule({
    name = "suppress-maximize-events",
    match = { class = ".*" },
    suppress_event = "maximize",
  })

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

  -- Screen-share picker opens at 1280x800 in a corner; keep it compact and centred.
  -- 500x400 (floating-small) truncates the monitor names and the four tabs.
  hl.window_rule({
    name = "share-picker",
    match = { class = "hyprland-share-picker" },
    float = true,
    size = { 760, 480 },
    center = true,
  })

  hl.window_rule({ name = "waydroid-fullscreen", match = { class = "Waydroid" }, fullscreen = true })
  hl.window_rule({ name = "overwatch-immediate", match = { title = "Overwatch" }, immediate = true })
  hl.layer_rule({
    name = "glassy-blur",
    match = { namespace = "rofi|waybar|notifications|tooltip" },
    blur = true,
    ignore_alpha = 0.005,
  })
end
