return {
-- Helps with intendation settings using editorconfig standard
{ "tpope/vim-sleuth" },
-- Enables support to manipulate surrounding text objects like cs'" will make 'text' -> "text"
{ "tpope/vim-surround" },
-- Gives some UNIX commands as helper functions for vi, such as :Rename :SudoWrite :Chmod etc
{ "tpope/vim-eunuch" },
-- Enables the default last command with period behaviour for custom mappings
{ "tpope/vim-repeat" },
-- Pairs of handy bracket mappings like [b or ]b
{ "tpope/vim-unimpaired" },
-- Remembers the last cursor position of the file
{ "farmergreg/vim-lastplace" },
-- Navigate between tmux pane and vim splits seamlessly <C-h,j,k,l>
{ "christoomey/vim-tmux-navigator" },
-- Enables * search for visually selected texts
{"nelstrom/vim-visual-star-search"},
-- Creates parent directories for a file if not exists
{"jessarcher/vim-heritage"},
-- More text objects for HTML and XML attributes so we can do `vix` to select an html attribute same goes fo c,y & d
{
'whatyouhide/vim-textobj-xmlattr',
dependencies = {'kana/vim-textobj-user'}
},
-- Adds closing brackets, quotes etc.
{
"windwp/nvim-autopairs",
config = function()
	require("nvim-autopairs").setup()
end,
},

-- Add smooth scrolling for jumps
{
"karb94/neoscroll.nvim",
config = function()
	require("neoscroll").setup()
end,
},
{
"famiu/bufdelete.nvim",
config = function()
vim.keymap.set('n', '<Leader>q', ':Bdelete<CR>')
end,
},

{
"sickill/vim-pasta",
config = function()
vim.g.pasta_disable_filetypes = { 'fugitive'}
end,
},

-- Can split and join arrays and methods into new lines or single line. TODO: it's asking for github username and password
-- {
-- "AndrewRadev/splitjoin.nvim",
-- config = function()
-- vim.g.splitjoin_html_attributes_bracket_on_new_line = 1
-- vim.g.splitjoin_trailing_comma = 1
-- vim.g.splitjoin_php_method_chain = 1
-- end,
-- },



{ "rafamadriz/friendly-snippets" },
-- { "sheerun/vim-polyglot" },--TODO: Needs Fixing


-- Catppuccin color scheme
{
"catppuccin/nvim",
name = "catppuccin",
priority = 1000,
},
-- One Dark Pro Color Scheme
{
  "joshdick/onedark.vim",
  priority = 1000, -- Ensure it loads first
config = function()
    vim.cmd.colorscheme("onedark")

    vim.api.nvim_set_hl(0, 'NvimTreeIndentMarker', { fg = '#30323E' })
    vim.api.nvim_set_hl(0, 'StatusLineNonText', {
      fg = vim.api.nvim_get_hl_by_name('NonText', true).foreground,
      bg = vim.api.nvim_get_hl_by_name('StatusLine', true).background,
    })
    vim.api.nvim_set_hl(0, 'IndentBlanklineChar', { fg = '#2F313C' })
end,
},
-- Displays indent line
{
  'lukas-reineke/indent-blankline.nvim',
    main = "ibl",
    ---@module "ibl"
    ---@type ibl.config
    opts = {
    },
},

{
"nathom/filetype.nvim",
opts = {
overrides = {
complex = {
["*.blade.php"] = "blade",
},
}
}
},
{
"mskelton/termicons.nvim",
dependecies = { "nvim-tree/nvim-web-devicons" },
build = false,
opts = {},
}
}
