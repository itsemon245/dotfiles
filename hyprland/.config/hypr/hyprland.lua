-- Candidate Hyprland Lua configuration. This directory is intentionally not active.

---@alias ApplyModule fun(settings: Dotfiles.Settings)

---@type Dotfiles.Settings
local settings = require("lua.settings")


---@type string[]
local module_names = {
  "lua.modules.monitors",
  "lua.modules.environment",
  "lua.modules.appearance",
  "lua.modules.animations",
  "lua.modules.input",
  "lua.modules.rules",
  "lua.modules.bindings",
  "lua.modules.startup",
}

for _, module_name in ipairs(module_names) do
  local loaded, apply_or_error = pcall(require, module_name)

  if loaded and type(apply_or_error) == "function" then
    ---@cast apply_or_error ApplyModule
    apply_or_error(settings)
  else
    print(string.format("Hyprland config: skipped %s: %s", module_name, tostring(apply_or_error)))
  end
end
