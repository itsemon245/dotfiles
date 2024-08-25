return {
	"nvim-treesitter/nvim-treesitter",
	build = ":TSUpdate",
	config = function()
		local treesitter = require("nvim-treesitter")
		require("nvim-treesitter.configs").setup({
			ensure_installed = { "php", "lua", "css", "html", "javascript", "typescript", "json" },
			sync_install = false,
			auto_install = false,
			ignore_install = {md},
			highlight = {
				enable = true,
			},
			indent = {
				enable = true,
			},
		})
		local parser_config = require("nvim-treesitter.parsers").get_parser_configs()
		parser_config.blade = {
			install_info = {
				url = "https://github.com/EmranMR/tree-sitter-blade",
				files = { "src/parser.c" },
				branch = "main",
			},
			filetype = "blade",
		}
	end,
}
