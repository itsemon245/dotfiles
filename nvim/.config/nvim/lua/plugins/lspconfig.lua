return {

  {
    "neovim/nvim-lspconfig",
    dependencies = {
      "WhoIsSethDaniel/mason-tool-installer.nvim",
      'hrsh7th/cmp-nvim-lsp',
      { 'williamboman/mason.nvim', config = true },
      { "j-hui/fidget.nvim",       opts = {} },
      {
        "williamboman/mason-lspconfig.nvim",
        lazy = false,
        opts = {
        },
      },
      {
        -- `lazydev` configures Lua LSP for your Neovim config, runtime and plugins
        -- used for completion, annotations and signatures of Neovim apis
        'folke/lazydev.nvim',
        ft = 'lua',
        opts = {
          library = {
            -- Load luvit types when the `vim.uv` word is found
            { path = 'luvit-meta/library', words = { 'vim%.uv' } },
          },
        },
      },
    },
    lazy = false,
    init = function()
      -- vim.g.coq_settings = {
      --   -- COQ settings here
      --   auto_start = true,
      --   display = {
      --     pum = {
      --       y_max_len = 5,
      --       x_max_len = 5,
      --     },
      --     preview = {
      --       border = "single",
      --       positions = {
      --         north = 4,
      --         south = nil,
      --         west = nil,
      --         east =  1
      --       },
      --     },
      --     icons = {
      --     }
      --   }
      -- }
    end,
    opts = {},
    config = function()
      -- LSP Logics
      local lspOnAttach = require("user.lsp.on_attach")
      -- Lsp configuration starts
      local default_capabilities = require('cmp_nvim_lsp').default_capabilities() --from nvim cpm
      -- local default_capabilities = require("coq").lsp_ensure_capabilities() --from coq
      local capabilities = vim.lsp.protocol.make_client_capabilities()
      capabilities = vim.tbl_deep_extend('force', capabilities, default_capabilities)

      vim.api.nvim_create_autocmd('LspAttach', {
        group = vim.api.nvim_create_augroup('kickstart-lsp-attach', { clear = true }),
        callback = lspOnAttach,
      })
      -- Enable this if you are not using nixos otherwise it will be installed using nixos
      local ensure_installed = vim.tbl_keys(require('user.lsp.servers') or {})
      require('mason-tool-installer').setup { ensure_installed = ensure_installed }

      require('mason').setup()
      require('mason-lspconfig').setup {
        ensure_installed = ensure_installed,
        automatic_installation = true,
        handlers = {
          function(server_name)
            -- import server from user/lsp/servers.lua
            local server = require("user.lsp.servers")[server_name]
            if server ~= nil then
              -- Remove nixpkg_name if not on nixos
              local is_nixos = require("user.helpers").is_nixos
              if not is_nixos then
                server.nixpkg_name = nil
                server.binary = nil
              end
              server.capabilities = vim.tbl_deep_extend('force', {}, capabilities, server.capabilities or {})
              require('lspconfig')[server_name].setup(server)
            end
          end,
        },
      }
    end
  },
}
