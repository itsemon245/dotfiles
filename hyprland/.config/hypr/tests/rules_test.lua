-- Tests lib/rules.lua and modules/rules.lua against a stub `hl`. Run: lua tests/rules_test.lua
---@diagnostic disable: missing-fields  (the mistake tests pass incomplete groups on purpose)
local root = debug.getinfo(1, "S").source:sub(2):match("^(.*)/tests/[^/]*$") or "."
package.path = root .. "/?.lua;" .. package.path
local recorded, notes = {}, {}
hl = { window_rule = function(r) recorded[#recorded + 1] = r end,
       layer_rule = function() end,
       notification = { create = function(n) notes[#notes + 1] = n.text end } }
_G.print = function() end
local rules = require("lua.lib.rules")
local function print_(s) io.write(s, "\n") end
local fails = 0
local function check(label, ok) if not ok then fails = fails + 1 end print_(string.format("%-58s %s", label, ok and "ok" or "FAIL")) end

-- 1. the real config, loaded exactly as Hyprland would
recorded, notes = {}, {}
require("lua.modules.rules")({})
local names = {}
for i, r in ipairs(recorded) do names[i] = r.name end
check("real config: rule order", table.concat(names, ",") ==
  "suppress-maximize-events,float-large,float-medium,float-small,float-small-window-1,waydroid-fullscreen,overwatch-immediate")
check("real config: no problems reported", #notes == 0)
check("real config: large classes exact", recorded[2].match.class ==
  "^(floating-lg|floating-large|xdg-desktop-portal-gtk|xdm-app)$")
check("real config: XDM dialog after every class rule", recorded[5].match.title:match("Download") and recorded[5].size[1] == 500)

-- 2. keyed + array entries, custom size, dotted class
recorded, notes = {}, {}
rules.floating({
  large = { size = { 800, 600 }, classes = { "a" } },
  picker = { size = { 760, 480 }, classes = { "Netsoft-com.netsoft.hubstaff" } },
  { name = "small", size = { 500, 400 }, windows = { { class = "xdm-app", title = "^Download" } } },
})
check("mixed formats: 3 rules, no problems", #recorded == 3 and #notes == 0)
local picker; for _, r in ipairs(recorded) do if r.name == "float-picker" then picker = r end end
check("custom group keeps its size", picker and picker.size[1] == 760)
check("dots are escaped (literal match)", picker and picker.match.class:find("hubstaff", 1, true) and picker.match.class:find("\\.netsoft", 1, true) ~= nil)
check("window rule comes last", recorded[3].name == "float-small-window-1" and recorded[3].match.class == "^(xdm-app)$")

-- 3. mistakes are reported and only that entry is skipped
local function problems(spec) local _, p = rules.normalise(spec) return p end
local p
p = problems({ large = { size = { 800, 600 }, classes = { "x" }, sise = { 1, 2 } } })
check("unknown key reported", #p == 1 and p[1]:find("unknown key"))
p = problems({ dialogs = { classes = { "x" } } })
check("group without size reported", #p == 1 and p[1]:find("no size"))
p = problems({ large = { classes = { "x" } } })
check("no preset sizes: even 'large' needs a size", #p == 1 and p[1]:find("no size"))
p = problems({ large = { size = { 800, 600 }, classes = { "x" } }, small = { size = { 500, 400 }, classes = { "x" } } })
check("class in two groups reported", #p == 1 and p[1]:find("both"))
p = problems({ large = { name = "small", size = { 800, 600 }, classes = { "x" } } })
check("key/name mismatch reported", #p == 1 and p[1]:find("also sets name"))
p = problems({ { size = { 800, 600 }, classes = { "x" } } })
check("unnamed array entry reported", #p == 1 and p[1]:find("unnamed"))
p = problems({ small = { size = { 500, 400 }, windows = { { title = "x" } } } })
check("window without class reported", #p == 1 and p[1]:find("windows%[1%]"))
p = problems({ large = { size = { 800 }, classes = { "x" } } })
check("bad size reported", #p == 1 and p[1]:find("size must be"))
recorded, notes = {}, {}
rules.floating({ large = { size = { 800, 600 }, classes = { "ok" } }, broken = { classes = { "y" } } })
check("bad group skipped, good one still applied", #recorded == 1 and recorded[1].name == "float-large" and #notes == 1)

print_(fails == 0 and "ALL PASSED" or (fails .. " FAILED"))
os.exit(fails == 0 and 0 or 1)
