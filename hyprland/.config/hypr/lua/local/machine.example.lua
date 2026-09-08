-- Copy this file to machine.lua. The destination is ignored by Git.
-- Use the connector name (for example DP-2) for a machine-local profile.
-- A desc: selector is useful when the same physical monitor moves between connectors.

---@type HL.MonitorSpec[]
return {
  {
    output = "DP-2",
    mode = "2560x1440@180",
    position = "0x0",
    scale = 1,
    vrr = 1,
  },
}
