-- return {}
return {
  {
    "L3MON4D3/LuaSnip",
    tag = "v2.*",
    run = "make install_jsregexp",
    dependencies = {
      "saadparwaiz1/cmp_luasnip",
      "rafamadriz/friendly-snippets",
      "onecentlin/laravel-blade-snippets-vscode",
    },
  },
  {
    "hrsh7th/nvim-cmp",
    dependencies = {
      -- Sources
      "hrsh7th/cmp-path",
      'hrsh7th/cmp-buffer',
      "hrsh7th/cmp-emoji",
      'hrsh7th/cmp-cmdline',
      'hrsh7th/cmp-nvim-lsp-signature-help',
      'hrsh7th/cmp-nvim-lsp-document-symbol',
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
      luasnip.filetype_extend('javascriptreact', { 'javascript' })
      luasnip.filetype_extend('typescriptreact', { 'typescript' })
      luasnip.filetype_extend("vue", { "html" })

      -- load vscode style snippets -- Uses the friendly-snippets repo
      require("luasnip.loaders.from_vscode").lazy_load()
      -- load snipmate style snippets -- Uses the snippets folder for custom snippets
      require("luasnip.loaders.from_snipmate").lazy_load({ paths = "~/.config/nvim/snippets" })
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
          ["<C-d>"] = cmp.mapping.scroll_docs(4),
          ["<C-u>"] = cmp.mapping.scroll_docs(-4),
          -- <C-space is used by tmux so I should use <C-p>
          ["<C-p"] = cmp.mapping.complete(),
          ["<C-e>"] = cmp.mapping.abort(),
          ["<CR>"] = cmp.mapping.confirm({ select = true }), -- Accept currently selected item. Set `select` to `false` to only confirm explicitly selected items.
        }),
        sources = cmp.config.sources({
          { name = 'nvim_lsp' },
          { name = "path" },
          { name = "buffer" },
          { name = "luasnip" }, -- snippets
          { name = "emoji" },
          { name = "nvim_lsp_signature_help" },
        }),
        -- Configure lspkind for vscode like pictograms in completion menu
        formatting = {
          format = lspkind.cmp_format({
            preset = "codicons", --vscode like icons
            -- mode = 'symbol', -- show only symbol annotations
            maxwidth = {
              -- prevent the popup from showing more than provided characters (e.g 50 will not show more than 50 characters)
              -- can also be a function to dynamically calculate max width such as
              -- menu = function() return math.floor(0.45 * vim.o.columns) end,
              menu = 50,              -- leading text (labelDetails)
              abbr = 50,              -- actual suggestion item
            },
            ellipsis_char = '...',    -- when popup menu exceed maxwidth, the truncated part would show ellipsis_char instead (must define maxwidth first)
            show_labelDetails = true, -- show labelDetails in menu. Disabled by default

            -- The function below will be called before any actual modifications from lspkind
            -- so that you can provide more controls on popup customization. (See [#30](https://github.com/onsails/lspkind-nvim/pull/30))
            before = function(entry, vim_item)
              return vim_item
            end
          }),
        },
      })

      -- Use buffer source for `/` and `?` (if you enabled `native_menu`, this won't work anymore).
      cmp.setup.cmdline({ '/', '?' }, {
        mapping = cmp.mapping.preset.cmdline(),
        sources = {
          { name = 'buffer' },
          { name = 'nvim_lsp_document_symbol' },
        }
      })

      -- Use cmdline & path source for ':' (if you enabled `native_menu`, this won't work anymore).
      cmp.setup.cmdline(':', {
        mapping = cmp.mapping.preset.cmdline(),
        sources = cmp.config.sources({
          { name = 'path' }
        }, {
          { name = 'cmdline' }
        }),
        matching = { disallow_symbol_nonprefix_matching = false }
      })
    end,
  },
}
