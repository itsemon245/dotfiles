---@meta

-- Put shared module contracts here once two or more modules need the same type.

---@alias Dotfiles.BindAction HL.Dispatcher|fun()

---@class Dotfiles.BindSpec
---@field keys string
---@field action Dotfiles.BindAction
---@field desc string
---@field options? HL.BindOptions
---@field group? Dotfiles.ManualGroup  show this binding's family as one manual row

---@class Dotfiles.FloatWindow
---@field class string        exact class
---@field title? string       regex

---@class Dotfiles.FloatGroup
---@field name? string        only for array entries; keyed groups take the key
---@field size integer[]      { width, height }
---@field classes? string[]   every window of these apps (exact classes)
---@field windows? Dotfiles.FloatWindow[]  only matching windows, applied after all classes

---@class Dotfiles.ResolvedFloatGroup  what lib/rules.lua applies after validation
---@field name string
---@field size integer[]
---@field classes string[]
---@field windows Dotfiles.FloatWindow[]

---@class Dotfiles.ManualGroup  one manual row for a family of bindings
---@field id string             bindings sharing an id show once
---@field keys string           e.g. "SUPER + 1…0"
---@field desc string
