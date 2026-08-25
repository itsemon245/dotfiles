-- Copy this file to machine.lua. The destination is ignored by Git.
-- Prefer a desc: selector from `hyprctl monitors all` over a connector name such as DP-2.

---@type HL.MonitorSpec[]
return {
  {
    output = "desc:REPLACE WITH THE MONITOR DESCRIPTION",
    mode = "2560x1440@180",
    position = "0x0",
    scale = 1,
    vrr = 1,
  },
}
