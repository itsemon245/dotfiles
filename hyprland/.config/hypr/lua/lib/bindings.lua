local M = {}

---@param command string
---@param rules? table<string, string|number|boolean>
---@return HL.Dispatcher
function M.exec(command, rules)
  return hl.dsp.exec_cmd(command, rules)
end

---@param spec Dotfiles.BindSpec
---@return HL.Keybind
function M.bind(spec)
  local options = spec.options or {}
  options.description = spec.desc
  return hl.bind(spec.keys, spec.action, options)
end

return M
