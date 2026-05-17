return {
  {
    "nvim-treesitter/nvim-treesitter",
    lazy = false,
    build = ":TSUpdate",
    config = function()
      require("nvim-treesitter").setup()

      local function register_blade_parser()
        require("nvim-treesitter.parsers").blade = {
          install_info = {
            url = "https://github.com/EmranMR/tree-sitter-blade",
            files = { "src/parser.c" },
            branch = "main",
          },
        }
      end

      register_blade_parser()

      vim.api.nvim_create_autocmd("User", {
        pattern = "TSUpdate",
        callback = function()
          register_blade_parser()
        end,
      })

      local filetypes = {
        "bash",
        "blade",
        "css",
        "go",
        "html",
        "javascript",
        "javascriptreact",
        "json",
        "lua",
        "markdown",
        "markdown_inline",
        "php",
        "phpdoc",
        "rust",
        "typescript",
        "typescriptreact",
        "vim",
        "vimdoc",
        "vue",
        "yaml",
      }

      vim.api.nvim_create_autocmd("FileType", {
        pattern = filetypes,
        group = vim.api.nvim_create_augroup("user-treesitter", { clear = true }),
        callback = function(event)
          local ok = pcall(vim.treesitter.start, event.buf)
          if ok then
            vim.bo[event.buf].indentexpr = "v:lua.require'nvim-treesitter'.indentexpr()"
          end
        end,
      })
    end,
  }
}
