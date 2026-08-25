local helper = require("lua.lib.bindings")

---@class Dotfiles.MouseBindOptions: HL.BindOptions
---@field mouse boolean

---@param settings Dotfiles.Settings
---@return nil
return function(settings)
  local app = settings.apps
  local command = settings.commands
  local manual_theme = "~/.config/rofi/hypr-keybinds.rasi"
  ---@type string[]
  local manual_rows = {}

  ---@param keys string
  ---@return string
  local function mod(keys)
    return settings.main_mod .. " + " .. keys
  end

  ---@param value string
  ---@return string
  local function shell_quote(value)
    return "'" .. value:gsub("'", "'\\''") .. "'"
  end

  local function show_manual()
    local quoted_rows = {}
    for _, row in ipairs(manual_rows) do
      quoted_rows[#quoted_rows + 1] = shell_quote(row)
    end
    local rows = table.concat(quoted_rows, " ")
    local rofi = "rofi -dmenu -i -matching fuzzy -no-normalize-match -p 'Hyprland keys'"
      .. " -mesg 'Search shortcuts · Escape closes'"
      .. " -theme " .. manual_theme
    hl.exec_cmd("printf '%s\\n' " .. rows .. " | " .. rofi)
  end

  ---@param spec Dotfiles.BindSpec
  local function bind(spec)
    helper.bind(spec)
    manual_rows[#manual_rows + 1] = string.format("%-24s  %s", spec.keys, spec.desc)
  end

  bind({ keys = mod("T"), action = helper.exec(app.terminal), desc = "Open terminal" })
  bind({ keys = mod("B"), action = helper.exec(app.browser), desc = "Open browser" })
  bind({ keys = mod("E"), action = helper.exec(app.file_manager), desc = "Open file manager" })
  bind({ keys = mod("M"), action = helper.exec(app.menu), desc = "Open application menu" })
  bind({ keys = mod("SPACE"), action = helper.exec(app.menu), desc = "Open application menu" })
  bind({ keys = mod("X"), action = hl.dsp.window.close(), desc = "Close active window" })
  bind({ keys = mod("Q"), action = hl.dsp.window.close(), desc = "Close active window" })
  bind({ keys = mod("R"), action = hl.dsp.exit(), desc = "Exit Hyprland" })
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

  local directions = { h = "l", j = "d", k = "u", l = "r" }
  for key, direction in pairs(directions) do
    bind({ keys = mod(key), action = hl.dsp.focus({ direction = direction }), desc = "Move focus " .. direction })
  end

  for workspace = 1, settings.workspace_count do
    local key = tostring(workspace % settings.workspace_count)
    bind({ keys = mod(key), action = hl.dsp.focus({ workspace = workspace }), desc = "Focus workspace " .. workspace })
    bind({ keys = mod("SHIFT + " .. key), action = hl.dsp.window.move({ workspace = workspace }), desc = "Move window to workspace " .. workspace })
  end

  bind({ keys = mod("S"), action = hl.dsp.workspace.toggle_special(settings.special_workspace), desc = "Toggle special workspace" })
  bind({ keys = mod("SHIFT + S"), action = hl.dsp.window.move({ workspace = "special:" .. settings.special_workspace }), desc = "Move window to special workspace" })
  bind({ keys = mod("SHIFT + L"), action = hl.dsp.focus({ workspace = "e+1" }), desc = "Focus next open workspace" })
  bind({ keys = mod("SHIFT + H"), action = hl.dsp.focus({ workspace = "e-1" }), desc = "Focus previous open workspace" })
  bind({ keys = mod("SHIFT + TAB"), action = hl.dsp.focus({ workspace = "e-1" }), desc = "Focus previous open workspace" })
  bind({ keys = mod("TAB"), action = hl.dsp.focus({ workspace = "e-1" }), desc = "Focus previous open workspace" })

  bind({ keys = mod("V"), action = helper.exec(command.clipboard_menu), desc = "Open clipboard history" })
  bind({ keys = mod("CTRL + S"), action = helper.exec("hyprshot -m window -c -o " .. settings.screenshot_directory), desc = "Capture active window" })
  bind({ keys = "CTRL + ALT + S", action = helper.exec("hyprshot -m output -c -o " .. settings.screenshot_directory), desc = "Capture active monitor" })
  bind({ keys = mod("ALT + S"), action = helper.exec("hyprshot -m region -o " .. settings.screenshot_directory), desc = "Capture region" })

  ---@type Dotfiles.MouseBindOptions
  local move_mouse = { mouse = true }
  ---@type Dotfiles.MouseBindOptions
  local resize_mouse = { mouse = true }
  bind({ keys = mod("mouse:272"), action = hl.dsp.window.drag(), desc = "Move window", options = move_mouse })
  bind({ keys = mod("mouse:273"), action = hl.dsp.window.resize(), desc = "Resize window", options = resize_mouse })
end
