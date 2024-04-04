return {
	"nvimtools/none-ls.nvim",
	config = function()
		local null_ls = require("null-ls")
		local b = null_ls.builtins
		local f = b.formatting
		local d = b.diagnostics
		-- local c = b.completion
		null_ls.setup({
			sources = {
				f.stylua,
				f.pint,
				f.prettier,
				f.blade_formatter,
			},
		})

		-- Set Keymap for formatting
		vim.keymap.set("n", "<leader>fc", vim.lsp.buf.format, { desc = "[Format] [C]urrent File" })
		vim.keymap.set("n", "<leader>fc", vim.lsp.buf.format, { desc = "[Format] [C]urrent File" })
	end,
}
