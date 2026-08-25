---@type Dotfiles.Theme
local fallback = {
  background = "rgb(1E1E2E)",
  foreground = "rgb(CDD6F4)",
  primary = "rgb(89B4FA)",
  secondary = "rgb(CBA6F7)",
  primary_dim = "rgba(89B4FA80)",
}

local loaded, generated = pcall(require, "lua.generated.theme")

if loaded
    and type(generated) == "table"
    and type(generated.background) == "string"
    and type(generated.foreground) == "string"
    and type(generated.primary) == "string"
    and type(generated.secondary) == "string"
    and type(generated.primary_dim) == "string"
then
  ---@cast generated Dotfiles.Theme
  return generated
end

return fallback
