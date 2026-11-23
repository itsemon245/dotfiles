local helper = require("lua.lib.bindings")
local Manual = require("lua.lib.manual")

---@class Dotfiles.MouseBindOptions: HL.BindOptions
---@field mouse boolean

---@param settings Dotfiles.Settings
---@return nil
return function(settings)
  local app = settings.apps
  local command = settings.commands
  local manual = Manual.new()

  ---@param keys string
  ---@return string
  local function mod(keys)
    return settings.main_mod .. " + " .. keys
  end

  local function show_manual()
    hl.exec_cmd(manual:command(command.keybind_manual))
  end

  ---@param spec Dotfiles.BindSpec
  local function bind(spec)
    helper.bind(spec)
    manual:add(spec.keys, spec.desc, spec.group)
  end

  bind({ keys = mod("T"), action = helper.exec(app.terminal), desc = "Open terminal" })
  bind({ keys = mod("B"), action = helper.exec(app.browser), desc = "Open browser" })
  bind({ keys = mod("E"), action = helper.exec(app.file_manager), desc = "Open file manager" })
  bind({ keys = mod("M"), action = helper.exec(app.menu), desc = "Open application menu" })
  bind({ keys = mod("SPACE"), action = helper.exec(app.menu), desc = "Open application menu" })
  bind({ keys = mod("X"), action = hl.dsp.window.close(), desc = "Close active window" })
  bind({ keys = mod("Q"), action = hl.dsp.window.close(), desc = "Close active window" })
  bind({ keys = mod("SHIFT + R"), action = helper.exec(command.logout), desc = "Log out" })
  bind({ keys = mod("SHIFT + T"), action = hl.dsp.window.float({ action = "toggle" }), desc = "Toggle floating" })
  bind({ keys = mod("F"), action = hl.dsp.window.fullscreen({ action = "toggle" }), desc = "Toggle fullscreen" })

  bind({ keys = mod("W"), action = helper.exec(command.wallpaper_menu), desc = "Choose wallpaper" })
  bind({ keys = mod("CTRL + W"), action = helper.exec(command.wallpaper_upscale_menu), desc = "Choose and upscale wallpaper" })
  bind({ keys = mod("O"), action = helper.exec(command.readable_window), desc = "Toggle readability mode" })
  bind({ keys = mod("SHIFT + V"), action = helper.exec(command.rofi_vpn), desc = "Open VPN menu" })
  bind({ keys = mod("SHIFT + M"), action = helper.exec(command.rofi_monitor), desc = "Open monitor menu" })
  bind({ keys = mod("SHIFT + B"), action = helper.exec(command.refresh_bar), desc = "Reload status bar" })
  bind({ keys = mod("SHIFT + W"), action = helper.exec(command.toggle_bar), desc = "Toggle status bar" })
  bind({ keys = mod("SHIFT + C"), action = helper.exec(command.regenerate_theme), desc = "Regenerate colors" })
  bind({ keys = mod("SLASH"), action = show_manual, desc = "Show binding manual" })
  -- Recovery when a rofi layer stops taking keys (IBus input-method grab gone stale).
  -- Compositor bindings are matched before keys reach the input method, so this still fires.
  bind({ keys = mod("CTRL + ESCAPE"), action = helper.exec(command.unstick_rofi), desc = "Unstick rofi and IBus" })

  local focus_group = { id = "focus", keys = mod("H / J / K / L"), desc = "Move focus left / down / up / right" }
  for _, pair in ipairs({ { "h", "l" }, { "j", "d" }, { "k", "u" }, { "l", "r" } }) do
    local key, direction = pair[1], pair[2]
    bind({ keys = mod(key), action = hl.dsp.focus({ direction = direction }), desc = "Move focus " .. direction, group = focus_group })
  end

  local last = tostring(settings.workspace_count % settings.workspace_count)
  local span = "1…" .. last
  local range = "1–" .. settings.workspace_count
  local focus_ws = { id = "focus-ws", keys = mod(span), desc = "Focus workspace " .. range }
  local move_ws = { id = "move-ws", keys = mod("SHIFT + " .. span), desc = "Move window to workspace " .. range }
  for workspace = 1, settings.workspace_count do
    local key = tostring(workspace % settings.workspace_count)
    bind({ keys = mod(key), action = hl.dsp.focus({ workspace = workspace }), desc = "Focus workspace " .. workspace, group = focus_ws })
    bind({ keys = mod("SHIFT + " .. key), action = hl.dsp.window.move({ workspace = workspace }), desc = "Move window to workspace " .. workspace, group = move_ws })
  end

  bind({ keys = mod("S"), action = hl.dsp.workspace.toggle_special(settings.special_workspace), desc = "Toggle special workspace" })
  bind({ keys = mod("SHIFT + S"), action = hl.dsp.window.move({ workspace = "special:" .. settings.special_workspace }), desc = "Move window to special workspace" })
  bind({ keys = mod("SHIFT + L"), action = hl.dsp.focus({ workspace = "e+1" }), desc = "Focus next open workspace" })
  bind({ keys = mod("SHIFT + H"), action = hl.dsp.focus({ workspace = "e-1" }), desc = "Focus previous open workspace" })
  bind({ keys = mod("SHIFT + TAB"), action = hl.dsp.focus({ workspace = "e-1" }), desc = "Focus previous open workspace" })
  bind({ keys = mod("TAB"), action = hl.dsp.focus({ workspace = "e-1" }), desc = "Focus previous open workspace" })

  bind({ keys = mod("V"), action = helper.exec(command.clipboard_menu), desc = "Open clipboard history" })
  bind({ keys = mod("CTRL + S"), action = helper.exec(command.screenshot_window), desc = "Capture active window" })
  bind({ keys = "CTRL + ALT + S", action = helper.exec(command.screenshot_monitor), desc = "Capture active monitor" })
  bind({ keys = mod("ALT + S"), action = helper.exec(command.screenshot_region), desc = "Capture region" })

  ---@type Dotfiles.MouseBindOptions
  local move_mouse = { mouse = true }
  ---@type Dotfiles.MouseBindOptions
  local resize_mouse = { mouse = true }
  bind({ keys = mod("mouse:272"), action = hl.dsp.window.drag(), desc = "Move window", options = move_mouse })
  bind({ keys = mod("mouse:273"), action = hl.dsp.window.resize(), desc = "Resize window", options = resize_mouse })
end
