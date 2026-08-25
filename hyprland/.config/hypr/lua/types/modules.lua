---@meta

-- Put shared module contracts here once two or more modules need the same type.

---@alias Dotfiles.BindAction HL.Dispatcher|fun()

---@class Dotfiles.BindSpec
---@field keys string
---@field action Dotfiles.BindAction
---@field desc string
---@field options? HL.BindOptions
