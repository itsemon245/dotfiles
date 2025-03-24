local opt = vim.opt
local g = vim.g

vim.cmd("set expandtab")
vim.cmd("set tabstop=2")
vim.cmd("set softtabstop=2")
vim.cmd("set shiftwidth=2")
vim.cmd("set autoindent")
vim.cmd("set cindent")
vim.cmd("set spellfile=~/.config/nvim/spell/en.utf-8.add")


-- Set <space> as the leader key
-- See `:help mapleader`
--  NOTE: Must happen before plugins are loaded (otherwise wrong leader will be used)
g.mapleader = " "
g.maplocalleader = " "

-- .blade.php file type to blade
vim.api.nvim_exec(
  [[
  au BufNewFile,BufRead *.blade.php setfiletype blade
]],
  false
)

g.have_nerd_font = true
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
vim.o.termguicolors = true

-- Folding --
opt.foldmethod = "expr"
opt.foldexpr = "v:lua.vim.treesitter.foldexpr()"
opt.foldenable = false
opt.foldlevel = 99
