return {
  {
    "williamboman/mason.nvim",
    lazy = false,
    opts = {},
  },
  {
    "williamboman/mason-lspconfig.nvim",
    lazy = false,
    opts = {
      ensure_installed = { "nil_ls", "html", "intelephense", "volar", "eslint", "tailwindcss" },
      auto_install = true,
    },
  },
  {
    "neovim/nvim-lspconfig",
    dependencies = {
      "WhoIsSethDaniel/mason-tool-installer.nvim",
      "ms-jpq/coq_nvim",
      { "j-hui/fidget.nvim", opts = {} },
      { "folke/neodev.nvim", opts = {} },
    },
    lazy = false,
    opts = {},
    config = function()
      local capabilities = require("cmp_nvim_lsp").default_capabilities()
      local lsp = require("lspconfig")
      local util = require("lspconfig/util")
      -- Lua
      lsp.lua_ls.setup({
        capabilities = capabilities,
      })
      --PHP
      lsp.phpactor.setup({
        capabilities = capabilities,
      })
      -- JS
      lsp.volar.setup({
        filetypes = { "typescript", "javascript", "javascriptreact", "typescriptreact", "vue" },
        capabilities = capabilities,
      })
      -- Tailwind
      lsp.tailwindcss.setup({
        capabilities = capabilities,
      })
      -- SQL
      lsp.sqls.setup({
        capabilities = capabilities,
      })
      -- Nix
      lsp.nil_ls.setup({
        capabilities = capabilities,
      })
      -- Go
      lsp.gopls.setup({
        capabilities = capabilities,
        cmd = { "gopls" },
        filetype = { "go", "gomod", "gowork", "gotmpl" },
        root_dir = util.root_pattern("go.work", "go.mod", ".git"),
        settings = {
          gopls = {
            completeUnimported = true,
            usePlaceholders = true,
            analyses = {
              unusedparams = true,
            },
          },
        },
      })
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
      -- Fuzzy find all the symbols in your current document.
      --  Symbols are things like variables, functions, types, etc.
      -- map("<leader>ds", require("telescope.builtin").lsp_document_symbols, "[D]ocument [S]ymbols")
      --  Similar to document symbols, except searches over your entire project.
      map("<leader>ws", require("telescope.builtin").lsp_dynamic_workspace_symbols, "[W]orkspace [S]ymbols")
      map("<leader>rn", vim.lsp.buf.rename, "[R]e[n]ame Variable")
      map("<leader>ca", vim.lsp.buf.code_action, "[C]ode [A]ction")
      map("K", vim.lsp.buf.hover, "Hover Documentation")

      --  This function gets run when an LSP attaches to a particular buffer.
      --    That is to say, every time a new file is opened that is associated with
      --    an lsp (for example, opening `main.rs` is associated with `rust_analyzer`) this
      --    function will be executed to configure the current buffer
      -- vim.api.nvim_create_autocmd("LspAttach", {
      --   group = vim.api.nvim_create_augroup("kickstart-lsp-attach", { clear = true }),
      --   callback = function(event)
      --     -- NOTE: Remember that Lua is a real programming language, and as such it is possible
      --     -- to define small helper and utility functions so you don't have to repeat yourself.
      --     --
      --     -- In this case, we create a function that lets us more easily define mappings specific
      --     -- for LSP related items. It sets the mode, buffer and description for us each time.
      --     -- The following two autocommands are used to highlight references of the
      --     -- word under your cursor when your cursor rests there for a little while.
      --     --    See `:help CursorHold` for information about when this is executed
      --     --
      --     -- When you move your cursor, the highlights will be cleared (the second autocommand).
      --     local client = vim.lsp.get_client_by_id(event.data.client_id)
      --     if client and client.server_capabilities.documentHighlightProvider then
      --       vim.api.nvim_create_autocmd({ "CursorHold", "CursorHoldI" }, {
      --         buffer = event.buf,
      --         callback = vim.lsp.buf.document_highlight,
      --       })
      --
      --       vim.api.nvim_create_autocmd({ "CursorMoved", "CursorMovedI" }, {
      --         buffer = event.buf,
      --         callback = vim.lsp.buf.clear_references,
      --       })
      --     end
      --   end,
      -- })
    end,
  },
}
