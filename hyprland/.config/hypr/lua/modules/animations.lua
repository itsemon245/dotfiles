---@param _settings Dotfiles.Settings
---@return nil
return function(_settings)
  hl.config({ animations = { enabled = true } })
  hl.curve("snappy", { type = "bezier", points = { { 0.05, 0.9 }, { 0.1, 1.1 } } })
  hl.animation({ leaf = "windows", enabled = true, speed = 4, bezier = "snappy" })
  hl.animation({ leaf = "windowsOut", enabled = true, speed = 4, bezier = "snappy", style = "popin 80%" })
  hl.animation({ leaf = "border", enabled = true, speed = 4, bezier = "default" })
  hl.animation({ leaf = "borderangle", enabled = true, speed = 8, bezier = "default" })
  hl.animation({ leaf = "fade", enabled = true, speed = 3, bezier = "default" })
  hl.animation({ leaf = "workspaces", enabled = true, speed = 4, bezier = "snappy" })
end
