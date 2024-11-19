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
      'chrisgrieser/cmp-nerdfont',
      -- Source for Luasnip choice nodes
      'L3MON4D3/cmp-luasnip-choice',
      'brenoprata10/nvim-highlight-colors',
      'onsails/lspkind.nvim'
    },
    config = function()
      -- Override the cord icons
      local lspkind = require("lspkind")
      -- local codicons = lspkind.presets.codicons
      local symbol_map = {
        Text = " ",
        Snippet = " ",
        Function = " ",
        Constructor = " ",
        Enum = " ",
        Interface = " ",
        File = " ",
        Keyword = " ",
        Supermaven = " "
      }
      -- for k, v in pairs(icons_to_override) do codicons[k] = v end
      -- lspkind.presets.codicons = codicons

      local cmp = require("cmp")
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
          -- <C-space is used by tmux so I should use <C-n>
          ["<C-n"] = cmp.mapping.complete(),
          ["<C-e>"] = cmp.mapping.abort(),
          ["<C-y>"] = cmp.mapping.confirm({ select = true }), -- Accept currently selected item. Set `select` to `false` to only confirm explicitly selected items.
          ["<CR>"] = cmp.mapping.confirm({ select = true }),  -- Accept currently selected item. Set `select` to `false` to only confirm explicitly selected items.
        }),
        experimental = {
          native_menu = false,
          ghost_text = false,
        },
        sources = cmp.config.sources({
          -- Order matters here
          { name = 'nvim_lsp' },
          { name = "nvim_lsp_signature_help" },
          { name = 'luasnip_choice' },
          {
            name = "luasnip",
            max_item_count = 6,
          },
          {
            name = "path",
            max_item_count = 6,
          },
          {
            name = "nerdfont",
            max_item_count = 6,
          },
          {
            name = "emoji",
            max_item_count = 6,
          },
          {
            name = "buffer",
            keyword_length = 4
          },
        }),
        -- Configure lspkind for vscode like pictograms in completion menu
        formatting = {
          fields = { "abbr", "kind", "menu" },
          expandable_indicator = true,
          format = lspkind.cmp_format({
            preset = "codicons", --vscode like icons
            -- mode = 'symbol', -- show only symbol annotations
            maxwidth = {
              menu = 50,
              abbr = 50,
            },
            symbol_map = symbol_map,
            ellipsis_char = '...',
            show_labelDetails = true,
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
