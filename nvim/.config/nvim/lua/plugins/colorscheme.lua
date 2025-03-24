return {
  "olimorris/onedarkpro.nvim",
  priority = 5000, -- Ensure it loads first
  config = function()
    require("onedarkpro").setup({
      -- colors = {
      --   -- Define custom colors to override the default ones
      --   cyan = "#00AFFF",
      --   blue = "#0087FF",
      -- },
      highlights = {
        -- Override spell highlighting to use blue/cyan instead of red
        SpellBad = { sp = "${cyan}", undercurl = true },
        SpellCap = { sp = "${blue}", undercurl = true },
        SpellRare = { sp = "${cyan}", undercurl = true },
        SpellLocal = { sp = "${blue}", undercurl = true },
      }
    })
    vim.cmd.colorscheme("onedark")
    
    -- These can be removed as they're now handled by the highlights config above
    -- vim.cmd.highlight("SpellBad gui=undercurl")

    vim.api.nvim_set_hl(0, 'NvimTreeIndentMarker', { fg = '#30323E' })
    vim.api.nvim_set_hl(0, 'IndentBlanklineChar', { fg = '#2F313C' })
  end,
}
