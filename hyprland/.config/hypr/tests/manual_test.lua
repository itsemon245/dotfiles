-- Tests lib/manual.lua through the real bindings.lua and settings.lua. Run: lua tests/manual_test.lua
local root = debug.getinfo(1, "S").source:sub(2):match("^(.*)/tests/[^/]*$") or "."
package.path = root .. "/?.lua;" .. package.path

local function stub() -- any hl.dsp.x.y(...) returns a placeholder dispatcher
  return setmetatable({}, { __index = function() return stub() end, __call = function() return {} end })
end
local binds, executed = {}, {}
hl = {
  dsp = stub(),
  bind = function(keys, action, options) binds[#binds + 1] = { keys = keys, action = action, desc = options.description } end,
  exec_cmd = function(cmd) executed[#executed + 1] = cmd end,
}

local tmp = os.tmpname()
os.remove(tmp)
local real_getenv = os.getenv
---@diagnostic disable-next-line: duplicate-set-field  point the rows file at a temp dir
os.getenv = function(name) return name == "XDG_RUNTIME_DIR" and tmp .. ".d" or real_getenv(name) end
os.execute("mkdir -p " .. tmp .. ".d")

local fails = 0
local function check(label, ok)
  if not ok then fails = fails + 1 end
  io.write(string.format("%-62s %s\n", label, ok and "ok" or "FAIL"))
end

require("lua.modules.bindings")(require("lua.settings"))
local show
for _, b in ipairs(binds) do
  if b.desc == "Show binding manual" then show = b.action end
end
check("Super + / is bound to a manual function", type(show) == "function")
show()
local cmd = executed[1] or ""
local path = cmd:match("%-input (%S+)$")
check("rofi reads the rows from a file", path ~= nil and cmd:find("-markup-rows", 1, true) ~= nil)

local rows = {}
for line in io.lines(path) do rows[#rows + 1] = line end
local search, display = {}, {}
for i, row in ipairs(rows) do
  search[i], display[i] = row:match("^(.-)%z" .. "display\31(.*)$")
end

check(string.format("%d bindings collapse into %d rows", #binds, #rows), #rows < #binds and #rows > 10)
local all_split = true
for i = 1, #rows do all_split = all_split and search[i] ~= nil and display[i] ~= nil end
check("every row has search text and a display string", all_split)

local plain_search = true
for _, s in ipairs(search) do plain_search = plain_search and not s:find("[<>]") end
check("search text never contains markup", plain_search)

local seen, dupes = {}, false
for _, s in ipairs(search) do
  local desc = s:match("^(.-)  ")
  if seen[desc] then dupes = true end
  seen[desc] = true
end
check("no description appears twice", not dupes)

local joined = table.concat(search, "\n")
check("workspaces collapse to one focus and one move row",
  joined:find("Focus workspace 1–10", 1, true) and joined:find("Move window to workspace 1–10", 1, true)
  and not joined:find("Focus workspace 3", 1, true))
check("h/j/k/l focus is one row", joined:find("Super + H / J / K / L", 1, true) ~= nil and not joined:find("Move focus u", 1, true))
check("key names are readable", joined:find("Super + /", 1, true) ~= nil and not joined:find("SLASH", 1, true)
  and joined:find("Left drag", 1, true) ~= nil)
check("shared actions merge keys, dropping shared modifiers", joined:find("Super + M / Space", 1, true) ~= nil
  and joined:find("Super + Shift + H / Shift + Tab / Tab", 1, true) ~= nil)

-- Columns line up: the description starts at the same visible column on every row.
local columns, aligned = {}, true
for _, d in ipairs(display) do
  local visible = d:gsub("<[^>]+>", ""):gsub("&lt;", "<"):gsub("&gt;", ">"):gsub("&amp;", "&")
  local desc_text = d:match('<span fgalpha="80%%">(.-)</span>$')
  local start = desc_text and visible:find(desc_text:gsub("&amp;", "&"), 1, true)
  columns[#columns + 1] = start and utf8.len(visible:sub(1, start - 1)) or -1
end
for _, c in ipairs(columns) do aligned = aligned and c == columns[1] and c > 0 end
check("descriptions start in one column", aligned)

os.execute("rm -rf " .. tmp .. ".d")
io.write(fails == 0 and "ALL PASSED\n" or (fails .. " FAILED\n"))
os.exit(fails == 0 and 0 or 1)
