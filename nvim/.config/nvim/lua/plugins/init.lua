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
}
