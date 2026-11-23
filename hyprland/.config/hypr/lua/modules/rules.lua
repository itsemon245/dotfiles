-- Floating group format: see "Window rules" in GUIDE.md.

local rules = require("lua.lib.rules")

local floating = {
  large = {
    size = { 800, 600 },
    classes = {
      "floating-lg", "floating-large",
      "xdg-desktop-portal-gtk",
      "xdm-app",
    },
  },
  medium = {
    size = { 760, 480 },
    classes = {
      "floating-md", "floating-medium",
      "hyprland-share-picker",
      "blueman-manager",
    },
  },
  small = {
    size = { 500, 400 },
    classes = { "floating-sm", "floating-small" },
    windows = {
      { class = "xdm-app", title = "^(?:[0-9]+%|Download|Confirm|Progress).*" },
    },
  },
}

---@param _settings Dotfiles.Settings
---@return nil
return function(_settings)
  -- kitty and others restore a remembered "maximized" state that covers the tiles.
  hl.window_rule({ name = "suppress-maximize-events", match = { class = ".*" }, suppress_event = "maximize" })

  rules.floating(floating)

  hl.window_rule({ name = "waydroid-fullscreen", match = { class = "Waydroid" }, fullscreen = true })
  hl.window_rule({ name = "overwatch-immediate", match = { title = "Overwatch" }, immediate = true })

  hl.layer_rule({
    name = "glassy-blur",
    match = { namespace = "rofi|waybar|notifications|tooltip" },
    blur = true,
    ignore_alpha = 0.005,
  })
end
