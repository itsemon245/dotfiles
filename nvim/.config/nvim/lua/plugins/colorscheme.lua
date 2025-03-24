return {
  "olimorris/onedarkpro.nvim",
  priority = 5000, -- Ensure it loads first
  config = function()
    require("onedarkpro").setup({

    })
    vim.cmd.colorscheme("onedark")
    vim.cmd.highlight("SpellBad gui=undercurl")

    vim.api.nvim_set_hl(0, 'NvimTreeIndentMarker', { fg = '#30323E' })
    vim.api.nvim_set_hl(0, 'IndentBlanklineChar', { fg = '#2F313C' })
  end,
}
