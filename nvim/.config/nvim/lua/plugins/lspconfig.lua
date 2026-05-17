return {
  {
    "neovim/nvim-lspconfig",
    dependencies = {
      "WhoIsSethDaniel/mason-tool-installer.nvim",
      { 'williamboman/mason.nvim', config = true },
      { "j-hui/fidget.nvim",       opts = {} },
      {
        "williamboman/mason-lspconfig.nvim",
        lazy = false,
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
    config = function()
      local lspOnAttach = require("user.lsp.on_attach")
      local servers = require('user.lsp.servers') or {}
      local capabilities = require("blink.cmp").get_lsp_capabilities()

      vim.g.lsp_capabilities = capabilities

      vim.api.nvim_create_autocmd('LspAttach', {
        group = vim.api.nvim_create_augroup('kickstart-lsp-attach', { clear = true }),
        callback = lspOnAttach,
      })

      -- Enable this if you are not using nixos otherwise it will be installed using nixos
      local ensure_installed = vim.tbl_keys(servers)
      require('mason-tool-installer').setup { ensure_installed = ensure_installed }

      require('mason').setup()
      require('mason-lspconfig').setup {
        ensure_installed = ensure_installed,
        automatic_enable = false,
      }

      local is_nixos = require("user.helpers").is_nixos()
      for server_name, server in pairs(servers) do
        local config = vim.deepcopy(server)
        if not is_nixos then
          config.nixpkg_name = nil
          config.binary = nil
        end

        config.capabilities = vim.tbl_deep_extend('force', {}, capabilities, config.capabilities or {})
        vim.lsp.config(server_name, config)
        vim.lsp.enable(server_name)
      end
    end
  },
}
