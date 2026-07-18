local opt = vim.opt
local g = vim.g

-- Set <space> as the leader key
-- See `:help mapleader`
--  NOTE: Must happen before plugins are loaded (otherwise wrong leader will be used)
g.mapleader = " "
g.maplocalleader = " "

vim.filetype.add({
  pattern = {
    [".*%.blade%.php"] = "blade",
  },
})

g.have_nerd_font = true

opt.expandtab = true
opt.tabstop = 2
opt.softtabstop = 2
opt.shiftwidth = 2
opt.autoindent = true
opt.cindent = true
opt.spellfile = vim.fn.stdpath("config") .. "/spell/en.utf-8.add"
opt.termguicolors = true

opt.smartindent = true
opt.spell = true

opt.wildmode =
'longest:full,full'                 -- complete the longest common match, and allow tabbing the results to fully complete them
opt.fillchars:append({ eob = ' ' }) -- remove the ~ from end of buffer

-- Lock the cursor to at least above 8 lines from bottom/up while scrolling
opt.scrolloff = 8
opt.sidescrolloff = 8

opt.confirm = true -- Confirm instead of error

opt.number = true
opt.relativenumber = true

opt.mouse = "a" -- Enable mouse mode, can be useful for resizing splits for example!

-- Don't show the mode, since it's already in the status line
opt.showmode = false

-- Sync clipboard between OS and Neovim.
opt.clipboard = "unnamedplus"

-- Enable break indent
opt.breakindent = true

-- Save undo history
opt.undofile = true

-- Case-insensitive searching UNLESS \C or one or more capital letters in the search term
opt.ignorecase = true
opt.smartcase = true

-- Keep signcolumn on by default
opt.signcolumn = "yes:2"

-- Decrease update time
opt.updatetime = 250

-- Decrease mapped sequence wait time
-- Displays which-key popup sooner
opt.timeoutlen = 300

-- Configure how new splits should be opened
opt.splitright = true
opt.splitbelow = true

-- Sets how neovim will display certain whitespace characters in the editor.
--  See `:help 'list'`
--  and `:help 'listchars'`
opt.list = true
opt.listchars = { tab = "» ", trail = "·", nbsp = "␣" }

-- Preview substitutions live, as you type!
opt.inccommand = "split"

-- Show which line your cursor is on
opt.cursorline = true

-- Folding --
opt.foldmethod = "expr"
opt.foldexpr = "v:lua.vim.treesitter.foldexpr()"
opt.foldenable = false
opt.foldlevel = 99

-- Disable unused providers --
g.loaded_node_provider = 0
g.loaded_perl_provider = 0
g.loaded_python3_provider = 0
g.loaded_ruby_provider = 0

--
--Wrapping --
--
-- Enable line wrapping
vim.opt.wrap = true
-- Prevent wrapping from breaking words in the middle
vim.opt.linebreak = true
-- Indent wrapped lines to match the start of the line
vim.opt.breakindent = true
-- Visual prefix for wrapped lines (optional)
vim.opt.showbreak = "↳ "
