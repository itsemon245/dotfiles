return {
  {
    'nvim-treesitter/playground',
    cmd = 'TSPlaygroundToggle',
    opts = {}
  },
  {
    "nvim-treesitter/nvim-treesitter",
    build = ":TSUpdate",
    dependencies = {
      "JoosepAlviste/nvim-ts-context-commentstring",
      "nvim-treesitter/nvim-treesitter-textobjects",
      "HiPhish/nvim-ts-rainbow2",
    },
    config = function()
      require("nvim-treesitter.configs").setup({
        modules = {},
        ignore_install = {},
        ensure_installed = {
          "php",
          "vim",
          "regex",
          "bash",
          "markdown",
          "markdown_inline",
          "phpdoc",
          "lua",
          "css",
          "html",
          "markdown",
          "javascript",
          "typescript",
          "tsx",
          "json",
          "yaml",
          "vue",
          "go",
          "rust",
        },
        sync_install = false,
        auto_install = true,
        highlight = {
          enable = true,
          -- Don't disable tsx highlighting
          additional_vim_regex_highlighting = false,
        },
        indent = {
          enable = true,
        },
        textobjects = {
          select = {
            enable = true,
            -- lookahead = true,
            keymaps = {
              ["if"] = "@function.inner",
              ["af"] = "@function.outer",
              ["ia"] = "@parameter.inner",
              ["aa"] = "@parameter.outer",
            },
          },
        },
        rainbow = {
          enable = false,
          -- list of languages you want to disable the plugin for
          disable = { "jsx", "tsx", "cpp" },
          -- Which query to use for finding delimiters
          query = "rainbow-parens",
          -- Highlight the entire buffer all at once
          strategy = require("ts-rainbow").strategy.global,
          hlgroups = {
            "TSRainbowYellow",
            "TSRainbowBlue",
            "TSRainbowOrange",
            "TSRainbowGreen",
            "TSRainbowViolet",
            "TSRainbowCyan",
          },
        },
      })
      local parser_config = require("nvim-treesitter.parsers").get_parser_configs()
      parser_config.blade = {
        install_info = {
          url = "https://github.com/EmranMR/tree-sitter-blade",
          files = { "src/parser.c" },
          branch = "main",
        },
        filetype = "blade",
      }
    end,
  }
}
