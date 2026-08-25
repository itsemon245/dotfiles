---@param _settings Dotfiles.Settings
---@return nil
return function(_settings)
  -- This must be registered first: it keeps an unknown display usable on a new machine.
  ---@type HL.MonitorSpec
  local fallback = {
    output = "",
    mode = "preferred",
    position = "auto",
    scale = 1,
  }

  hl.monitor(fallback)

  -- A local profile is optional. Copy lua/local/machine.example.lua to
  -- lua/local/machine.lua and replace its placeholder display description.
  local loaded, profile_or_error = pcall(require, "lua.local.machine")
  if not loaded then
    print(string.format("Hyprland monitor profile: using fallback (%s)", tostring(profile_or_error)))
    return
  end

  if type(profile_or_error) ~= "table" then
    print("Hyprland monitor profile: ignored non-table profile")
    return
  end

  ---@cast profile_or_error HL.MonitorSpec[]
  for _, monitor in ipairs(profile_or_error) do
    hl.monitor(monitor)
  end
end
