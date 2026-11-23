-- Window-rule helpers. Group format and ordering guarantees: "Window rules" in GUIDE.md.

local M = {}

local GROUP_KEYS = { name = true, size = true, classes = true, windows = true }
local WINDOW_KEYS = { class = true, title = true }

--- Escape a class so it matches literally (dots in reverse-DNS classes included).
---@param text string
---@return string
function M.literal(text)
  return (text:gsub("[%^%$%(%)%.%[%]%*%+%?{}|\\]", "\\%0"))
end

---@param names string[]
---@return string
local function exact(names)
  local escaped = {}
  for index, name in ipairs(names) do
    escaped[index] = M.literal(name)
  end
  return "^(" .. table.concat(escaped, "|") .. ")$"
end

---@param size any
---@return boolean
local function valid_size(size)
  return type(size) == "table" and #size == 2
    and math.type(size[1]) == "integer" and math.type(size[2]) == "integer"
    and size[1] > 0 and size[2] > 0
end

---@param value any
---@return boolean
local function string_list(value)
  if type(value) ~= "table" then
    return false
  end
  for _, item in ipairs(value) do
    if type(item) ~= "string" or item == "" then
      return false
    end
  end
  return true
end

--- Validate and normalise groups. Pure (no `hl`), so it can be tested outside Hyprland.
---@param spec table<string|integer, Dotfiles.FloatGroup>
---@return Dotfiles.ResolvedFloatGroup[] groups sorted by name
---@return string[] problems
function M.normalise(spec)
  local groups, problems, seen_names, class_owner = {}, {}, {}, {}

  local entries = {}
  for key, group in pairs(spec) do
    entries[#entries + 1] = { key = key, group = group }
  end

  for _, entry in ipairs(entries) do
    local key, group = entry.key, entry.group
    local name = type(key) == "string" and key or (type(group) == "table" and group.name) or nil
    local problem

    if type(group) ~= "table" then
      problem = string.format("group %s is not a table", tostring(key))
    elseif type(name) ~= "string" or name == "" then
      problem = "an unnamed group (array entries need `name = ...`)"
    elseif type(key) == "string" and group.name ~= nil and group.name ~= key then
      problem = string.format("group %s also sets name = %q", key, tostring(group.name))
    elseif seen_names[name] then
      problem = string.format("group %s is defined twice", name)
    else
      for field in pairs(group) do
        if not GROUP_KEYS[field] then
          problem = string.format("group %s: unknown key %q (use size, classes, windows)", name, tostring(field))
          break
        end
      end
    end

    local size = (not problem) and group.size or nil
    if not problem and not valid_size(size) then
      problem = group.size and string.format("group %s: size must be { width, height } in pixels", name)
        or string.format("group %s has no size; add size = { width, height }", name)
    end
    if not problem and group.classes ~= nil and not string_list(group.classes) then
      problem = string.format("group %s: classes must be a list of class names", name)
    end
    if not problem and group.windows ~= nil then
      if type(group.windows) ~= "table" then
        problem = string.format("group %s: windows must be a list of { class, title }", name)
      else
        for index, window in ipairs(group.windows) do
          local bad = type(window) ~= "table" or type(window.class) ~= "string"
            or (window.title ~= nil and type(window.title) ~= "string")
          if not bad then
            for field in pairs(window) do
              bad = bad or not WINDOW_KEYS[field]
            end
          end
          if bad then
            problem = string.format("group %s: windows[%d] must be { class = ..., title = ... }", name, index)
            break
          end
        end
      end
    end
    if not problem then
      for _, class in ipairs(group.classes or {}) do
        if class_owner[class] then
          problem = string.format("class %q is in both %s and %s; keep it in one group", class, class_owner[class], name)
          break
        end
      end
    end

    if problem then
      problems[#problems + 1] = problem
    else
      ---@cast name string  every problem-free path above has a name
      seen_names[name] = true
      for _, class in ipairs(group.classes or {}) do
        class_owner[class] = name
      end
      groups[#groups + 1] = { name = name, size = size, classes = group.classes or {}, windows = group.windows or {} }
    end
  end

  table.sort(groups, function(a, b) return a.name < b.name end)
  table.sort(problems)
  return groups, problems
end

---@param problems string[]
local function report(problems)
  if #problems == 0 then
    return
  end
  local text = "Window rules skipped:\n- " .. table.concat(problems, "\n- ")
  print(text)
  -- pcall: a failing notification must never stop the rest of the config loading.
  if hl.notification and hl.notification.create then
    pcall(hl.notification.create, { text = text, timeout = 10000 })
  end
end

--- Register centred floating rules for every group. Returns what was applied.
---@param spec table<string|integer, Dotfiles.FloatGroup>
---@return Dotfiles.ResolvedFloatGroup[]
function M.floating(spec)
  local groups, problems = M.normalise(spec)
  ---@param name string
  ---@param match table
  ---@param size integer[]
  local function rule(name, match, size)
    hl.window_rule({ name = name, match = match, float = true, size = size, center = true })
  end

  for _, group in ipairs(groups) do
    if #group.classes > 0 then
      rule("float-" .. group.name, { class = exact(group.classes) }, group.size)
    end
  end
  -- After every class rule, so these narrower matches win.
  for _, group in ipairs(groups) do
    for index, window in ipairs(group.windows) do
      local match = { class = exact({ window.class }), title = window.title }
      rule(string.format("float-%s-window-%d", group.name, index), match, group.size)
    end
  end

  report(problems)
  return groups
end

return M
