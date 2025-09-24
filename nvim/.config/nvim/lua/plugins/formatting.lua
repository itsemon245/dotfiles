-- Linter and Formatter
local event = {
  "BufReadPre",
  "BufNewFile"
}
return {
  -- Linter
  {
    'mfussenegger/nvim-lint',
    event = event,
    opts = {
      linters_by_ft = {
        lua = { 'luacheck' },
        php = { 'psalm' },
        javascript = { 'eslint_d' },
        typescript = { 'eslint_d' },
      }
    },
    config = function()
      vim.api.nvim_create_autocmd({ "BufWritePost" }, {
        callback = function()
          require("lint").try_lint()
        end,
      })
    end
  },
  -- Formatter
  {
    'stevearc/conform.nvim',
    event = event,
    opts = {
      format_on_save = {
        -- These options will be passed to conform.format()
        timeout_ms = 500,
        lsp_format = "fallback",
      },
      formatters_by_ft = {
        lua = { 'stylua' },
        blade = { 'blade-formatter' },
        sql = { 'sql-formatter' },
        nix = { 'nixpkgs-fmt' },
        php = { 'pint' },
        javascript = { 'prettier', 'prettierd' },
        typescript = { 'prettier', 'prettierd' },
        typescriptreact = { 'prettier', 'prettierd' },
        yaml = { 'yamlfmt', 'prettier', 'prettierd' },
        yml = { 'yamlfmt', 'prettier', 'prettierd' },
        json = { 'prettier', 'prettierd' },
        markdown = { 'prettier', 'prettierd' },
        md = { 'prettier', 'prettierd' },
        html = { 'prettier', 'prettierd' },
        css = { 'prettier', 'prettierd' },
        scss = { 'prettier', 'prettierd' },
      }
    },
    config = function()
      local conform = require('conform')
      vim.api.nvim_create_autocmd("BufWritePre", {
        pattern = "*",
        callback = function(args)
          conform.format({
            lsp_fallback = true,
            timeout_ms = 2000,
            async = false,
            bufnr = args.buf
          })
        end,
      })
      vim.keymap.set(
        { 'n', 'v' },
        '<leader>fc',
        function()
          conform.format({
            lsp_fallback = true,
            timeout_ms = 2000,
            async = false
          })
        end,
        { desc = "[F]ormat [C]ode" }
      )
    end
  }
}
