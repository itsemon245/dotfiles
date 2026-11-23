-- Builds the searchable keybinding manual (Super + /) from binding specs.
--
-- Each rofi row is `search text \0display\x1f markup`: rofi shows the markup but
-- filters on the plain text, so the formatting never matches a search.

local M = {}

local KEY_NAMES = {
  SUPER = "Super", SHIFT = "Shift", CTRL = "Ctrl", CONTROL = "Ctrl", ALT = "Alt",
  SLASH = "/", SPACE = "Space", TAB = "Tab", ESCAPE = "Esc", RETURN = "Enter",
  ["mouse:272"] = "Left drag", ["mouse:273"] = "Right drag",
}

--- "SUPER + SHIFT + SLASH" -> { "Super", "Shift", "/" }
---@param keys string
---@return string[]
function M.key_names(keys)
  local names = {}
  for raw in keys:gmatch("[^+]+") do
    local token = raw:match("^%s*(.-)%s*$")
    names[#names + 1] = KEY_NAMES[token] or KEY_NAMES[token:upper()] or (#token == 1 and token:upper() or token)
  end
  return names
end

---@param text string
---@return string
function M.escape(text)
  return (text:gsub("&", "&amp;"):gsub("<", "&lt;"):gsub(">", "&gt;"))
end

---@class Dotfiles.Manual
---@field entries { keys: string[], desc: string }[]  rows in binding order
---@field by_desc table<string, { keys: string[], desc: string }>
---@field groups table<string, boolean>  group ids already shown
local Manual = {}
Manual.__index = Manual

---@return Dotfiles.Manual
function M.new()
  return setmetatable({ entries = {}, by_desc = {}, groups = {} }, Manual)
end

--- Record a binding. Bindings with the same description share one row; a `group`
--- ({ id, keys, desc }) collapses a family (workspaces 1-10, h/j/k/l) into one row.
---@param keys string
---@param desc string
---@param group? Dotfiles.ManualGroup
function Manual:add(keys, desc, group)
  if group then
    if not self.groups[group.id] then
      self.groups[group.id] = true
      self.entries[#self.entries + 1] = { keys = { group.keys }, desc = group.desc }
    end
    return
  end
  local entry = self.by_desc[desc]
  if entry then
    entry.keys[#entry.keys + 1] = keys
  else
    entry = { keys = { keys }, desc = desc }
    self.by_desc[desc] = entry
    self.entries[#self.entries + 1] = entry
  end
end

local DIM = '<span fgalpha="45%%">%s</span>'

---@param names string[]
---@return string plain, string markup
local function render_keys(names)
  local marked = {}
  for index, name in ipairs(names) do
    marked[index] = "<b>" .. M.escape(name) .. "</b>"
  end
  return table.concat(names, " + "), table.concat(marked, DIM:format(" + "))
end

--- Leading modifiers every alternative shares, so later ones can omit them:
--- { Super M }, { Super Space } -> 1, shown as "Super + M / Space".
---@param alternatives string[][]
---@return integer
local function shared_prefix(alternatives)
  local count = 0
  while true do
    local token = alternatives[1][count + 1]
    for _, names in ipairs(alternatives) do
      if names[count + 1] ~= token or #names <= count + 1 then
        return count
      end
    end
    count = count + 1
  end
end

--- Rows ready for `rofi -dmenu -markup-rows -input`, keys padded into one column.
---@return string[]
function Manual:rows()
  local rendered, width = {}, 0
  for index, entry in ipairs(self.entries) do
    local alternatives = {}
    for i, keys in ipairs(entry.keys) do
      alternatives[i] = M.key_names(keys)
    end
    local shared = shared_prefix(alternatives)
    local plains, marks = {}, {}
    for i, names in ipairs(alternatives) do
      plains[i], marks[i] = render_keys(i == 1 and names or { table.unpack(names, shared + 1) })
    end
    local plain = table.concat(plains, " / ")
    rendered[index] = { plain = plain, markup = table.concat(marks, DIM:format(" / ")), desc = entry.desc }
    width = math.max(width, utf8.len(plain) or #plain)
  end
  local rows = {}
  for index, row in ipairs(rendered) do
    local pad = string.rep(" ", width - (utf8.len(row.plain) or #row.plain) + 3)
    local display = row.markup .. pad .. '<span fgalpha="80%">' .. M.escape(row.desc) .. "</span>"
    rows[index] = row.desc .. "  " .. row.plain .. "\0display\31" .. display
  end
  return rows
end

--- Write the rows to $XDG_RUNTIME_DIR and return `rofi_command` reading them.
--- Rows hold NUL bytes (rofi's row options), so they go through a file, not argv.
---@param rofi_command string
---@return string
function Manual:command(rofi_command)
  local path = (os.getenv("XDG_RUNTIME_DIR") or "/tmp") .. "/hypr-keybinds.rows"
  local file = io.open(path, "w")
  if not file then
    return "notify-send 'Keybinding manual' 'Could not write " .. path .. "'"
  end
  file:write(table.concat(self:rows(), "\n"), "\n")
  file:close()
  return rofi_command .. " -input " .. path
end

return M
