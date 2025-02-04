return {
  -- gopls = {
  --   settings = {
  --     gopls = {
  --       completeUnimported = true,
  --       usePlaceholders = true,
  --       analyses = {
  --         unusedparams = true,
  --       },
  --     },
  --   },
  -- },
  emmet_ls = {
    filetypes = { "html", "css", "javascript", "typescript", "javascriptreact", "typescriptreact", "vue", "svelte", "blade" },
  },
  tailwindcss = {
    filetypes = { "html", "css", "javascript", "typescript", "blade", "typescriptreact", "javascriptreact", "vue", "svelte" }
  },
  yamlls = {
    filetypes = { "yaml" },
    settings = {
      yaml = {
        schemas = {
          ["https://json.schemastore.org/github-workflow.json"] = "/.github/workflows/*.yml",
          ["https://json.schemastore.org/github-action.json"] = "/.github/action.yml",
          ["https://json.schemastore.org/ansible-stable-2.9"] = "/*.yml",
          ["https://raw.githubusercontent.com/composer/xdebug-handler/2/res/schema.json"] = "/composer.json",
        },
      },
    }
  },
  volar = {
    filetypes = {
      -- "typescript",
      -- "javascript",
      -- "javascriptreact",
      -- "typescriptreact",
      "vue"
    },
  },
  ts_ls = {
    filetypes = {
      "typescript",
      "javascript",
      "javascriptreact",
      "typescriptreact",
      -- "vue"
    },
  },
  -- LSPs for PHP
  -- psalm = {
  --   nixpkg_name = "php83Packages.psalm",
  --   cmd = { "psalm.phar", "--language-server" },
  --   filetypes = { "php" },
  -- },
  intelephense = { filetypes = { "php", "blade" } },
  -- phpactor = { filetypes = { "php", "blade" } },
  -- LSPs for Lua
  lua_ls = {
    settings = {
      Lua = {
        completion = {
          callSnippet = 'Replace',
        },
        -- You can toggle below to ignore Lua_LS's noisy `missing-fields` warnings
        diagnostics = {
          disable = {
            'missing-fields'
          }
        },
      },
    },
  },
}
