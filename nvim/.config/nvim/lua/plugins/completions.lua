-- return {}
return {
  {
    "hrsh7th/cmp-nvim-lsp",
  },
  {
    "L3MON4D3/LuaSnip",
    dependencies = {
      "saadparwaiz1/cmp_luasnip",
      "rafamadriz/friendly-snippets",
      "onecentlin/laravel-blade-snippets-vscode",
    },
  },
  {
    "hrsh7th/nvim-cmp",
    dependencies = {
      "hrsh7th/cmp-path",
      'hrsh7th/cmp-buffer',
      'brenoprata10/nvim-highlight-colors',
      'onsails/lspkind.nvim'
    },
    config = function()
      -- Set up nvim-cmp.
      local luasnip = require("luasnip")
      local lspkind = require("lspkind")
      local cmp = require("cmp")

      luasnip.filetype_extend("html", { "javascript" })
      luasnip.filetype_extend("php", { "html" })
      luasnip.filetype_extend("php", { "phpdoc" })
      luasnip.filetype_extend("php", { "blade" })
      luasnip.filetype_extend('javascriptreact', {'javascript'})
      luasnip.filetype_extend('typescriptreact', {'typescript'})
      luasnip.filetype_extend("vue", { "html" })
      require("luasnip.loaders.from_vscode").lazy_load()

      cmp.setup({
        completion = {
          completeopt = "menu,menuone,preview,noselect",
        },
        snippet = {
          -- REQUIRED - you must specify a snippet engine
          expand = function(args)
            require("luasnip").lsp_expand(args.body) -- For `luasnip` users.
          end,
        },
        window = {
          completion = cmp.config.window.bordered(),
          documentation = cmp.config.window.bordered(),
        },
        mapping = cmp.mapping.preset.insert({
          ["<C-d>"] = cmp.mapping.scroll_docs(-4),
          ["<C-u>"] = cmp.mapping.scroll_docs(4),
          -- <C-space is used by tmux so I should use <C-p>
          ["<C-p"] = cmp.mapping.complete(),
          ["<C-e>"] = cmp.mapping.abort(),
          ["<CR>"] = cmp.mapping.confirm({ select = true }), -- Accept currently selected item. Set `select` to `false` to only confirm explicitly selected items.
        }),
        sources = cmp.config.sources({
          {name = 'nvim_lsp'},
          { name = "path" },
          {name  = "buffer"},
          { name = "luasnip" }, -- snippets
        }),
        -- Configure lspkind for vscode like pictograms in completion menu
        formatting = {
          format = lspkind.cmp_format({
            maxwidth = 50,
            ellipsis_char = "...",
          }),
        },
      })
    end,
  },
}
