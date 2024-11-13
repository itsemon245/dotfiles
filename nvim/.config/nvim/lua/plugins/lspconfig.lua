return {

  {
    "neovim/nvim-lspconfig",
    dependencies = {
      "WhoIsSethDaniel/mason-tool-installer.nvim",
      'hrsh7th/cmp-nvim-lsp',
      "ms-jpq/coq_nvim",
      { 'williamboman/mason.nvim', config = true },
      { "j-hui/fidget.nvim", opts = {} },
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

      -- Coq for completion menu
      { "ms-jpq/coq_nvim", branch = "coq" },
      -- 9000+ Snippets
      { "ms-jpq/coq.artifacts", branch = "artifacts" },
      -- lua & third party sources -- See https://github.com/ms-jpq/coq.thirdparty
      -- Need to **configure separately**
      { 'ms-jpq/coq.thirdparty', branch = "3p" }
      -- - shell repl
      -- - nvim lua api
      -- - scientific calculator
      -- - comment banner
      -- - etc
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
      -- Lsp configuration starts
      local lsp = require("lspconfig")
      local util = require("lspconfig/util")
      local default_capabilities = require('cmp_nvim_lsp').default_capabilities() --from nvim cpm
      -- local default_capabilities = require("coq").lsp_ensure_capabilities() --from coq
      local capabilities = vim.lsp.protocol.make_client_capabilities()
      capabilities = vim.tbl_deep_extend('force', capabilities, default_capabilities)

      --  This function gets run when an LSP attaches to a particular buffer.
      --    That is to say, every time a new file is opened that is associated with
      --    an lsp (for example, opening `main.rs` is associated with `rust_analyzer`) this
      --    function will be executed to configure the current buffer

      vim.api.nvim_create_autocmd('LspAttach', {
        group = vim.api.nvim_create_augroup('kickstart-lsp-attach', { clear = true }),
        callback = function(event)
          local client = vim.lsp.get_client_by_id(event.data.client_id)
          client.server_capabilities.hoverProvider = true
          -- Enable completion triggered by <c-x><c-o>
          vim.api.nvim_buf_set_option(event.buf, 'omnifunc', 'v:lua.vim.lsp.omnifunc')

          -- Diagnostic configuration
          vim.diagnostic.config({
            virtual_text = false,
            float = {
              source = true,
            },
          })
          -- Sign configuration
          vim.fn.sign_define("DiagnosticSignError", { text = "", texthl = "DiagnosticSignError" })
          vim.fn.sign_define("DiagnosticSignWarn", { text = "", texthl = "DiagnosticSignWarn" })
          vim.fn.sign_define("DiagnosticSignInfo", { text = "", texthl = "DiagnosticSignInfo" })
          vim.fn.sign_define("DiagnosticSignHint", { text = "", texthl = "DiagnosticSignHint" })

          -- Utilty function for keymap
          local map = function(keys, func, desc)
            vim.keymap.set("n", keys, func, { desc = "LSP: " .. desc })
          end

          map("gd", require("telescope.builtin").lsp_definitions, "[G]oto [D]efinition")
          map("gD", vim.lsp.buf.declaration, "[G]oto [D]eclaration")
          map("gr", require("telescope.builtin").lsp_references, "[G]oto [R]eferences")
          map("gI", require("telescope.builtin").lsp_implementations, "[G]oto [I]mplementation")
          map("<Leader>d", "<cmd>lua vim.diagnostic.open_float()<CR>", "[D]iagnostics Popover")
          map("<leader>D", require("telescope.builtin").lsp_type_definitions, "Type [D]efinition")
          -- Go back and forth in code diagnostics
          map("[d", "<cmd>lua vim.diagnostic.goto_prev()<CR>", "Previous Diagnostics")
          map("]d", "<cmd>lua vim.diagnostic.goto_next()<CR>", "Next Diagnostics")
          --  Symbols are things like variables, functions, types, etc.
          map("<leader>ds", require("telescope.builtin").lsp_document_symbols, "[D]ocument [S]ymbols")
          map("<leader>ws", require("telescope.builtin").lsp_dynamic_workspace_symbols, "[W]orkspace [S]ymbols")
          map("<leader>rn", vim.lsp.buf.rename, "[R]e[n]ame Variable")
          map("<leader>ca", vim.lsp.buf.code_action, "[C]ode [A]ction")
          map("K", vim.lsp.buf.hover, "Hover Documentation")

          -- The following two autocommands are used to highlight references of the
          -- word under your cursor when your cursor rests there for a little while.
          --    See `:help CursorHold` for information about when this is executed
          --
          -- When you move your cursor, the highlights will be cleared (the second autocommand).
          local client = vim.lsp.get_client_by_id(event.data.client_id)
          if client and client.supports_method(vim.lsp.protocol.Methods.textDocument_documentHighlight) then
            local highlight_augroup = vim.api.nvim_create_augroup('kickstart-lsp-highlight', { clear = false })
            vim.api.nvim_create_autocmd({ 'CursorHold', 'CursorHoldI' }, {
              buffer = event.buf,
              group = highlight_augroup,
              callback = vim.lsp.buf.document_highlight,
            })

            vim.api.nvim_create_autocmd({ 'CursorMoved', 'CursorMovedI' }, {
              buffer = event.buf,
              group = highlight_augroup,
              callback = vim.lsp.buf.clear_references,
            })

            vim.api.nvim_create_autocmd('LspDetach', {
              group = vim.api.nvim_create_augroup('kickstart-lsp-detach', { clear = true }),
              callback = function(event2)
                vim.lsp.buf.clear_references()
                vim.api.nvim_clear_autocmds { group = 'kickstart-lsp-highlight', buffer = event2.buf }
              end,
            })
          end
          -- The following code creates a keymap to toggle inlay hints in your
          -- code, if the language server you are using supports them
          --
          -- This may be unwanted, since they displace some of your code
          if client and client.supports_method(vim.lsp.protocol.Methods.textDocument_inlayHint) then
            map('<leader>th', function()
              vim.lsp.inlay_hint.enable(not vim.lsp.inlay_hint.is_enabled { bufnr = event.buf })
            end, '[T]oggle Inlay [H]ints')
          end
        end,
      })

      -- Setup LSP from user/lsp/servers.lua
      require('mason').setup()
      require('mason-lspconfig').setup {
        handlers = {
          function(server_name)
            -- import server from user/lsp/servers.lua
            local server = require("user.lsp.servers")[server_name]
            if server ~= nil then
              -- Remove nixpkg_name if not on nixos
              local is_nixos = require("user.helpers").is_nixos
              if not is_nixos then
                server.nixpkg_name = nil
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
