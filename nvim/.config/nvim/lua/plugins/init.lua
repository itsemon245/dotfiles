return {
	{ "tpope/vim-sleuth" },
	{ "rafamadriz/friendly-snippets" },
	{ "tpope/vim-surround" },
	{
		"windwp/nvim-autopairs",
		config = function()
			local notify = require("nvim-autopairs")
		end,
	},
	{
		"catppuccin/nvim",
		name = "catppuccin",
		priority = 1000,
		config = function()
			vim.cmd.colorscheme("catppuccin")
		end,
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
		"nvim-lualine/lualine.nvim",
		dependencies = { "nvim-tree/nvim-web-devicons" },
		opts = {
			options = {
				theme = "catppuccin",
			},
		},
	},
	{
		"mskelton/termicons.nvim",
		dependecies = { "nvim-tree/nvim-web-devicons" },
		build = false,
		opts = {},
	}
}
