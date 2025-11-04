local schemastore = require('schemastore')
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
  --python
  pyright = {},
  yamlls = {
    filetypes = { "yaml" },
    settings = {
      yaml = {
        schemaStore = {
          -- You must disable built-in schemaStore support if you want to use
          -- this plugin and its advanced options like `ignore`.
          enable = false,
          -- Avoid TypeError: Cannot read properties of undefined (reading 'length')
          url = "",
        },
        schemas = schemastore.yaml.schemas(),
        -- schemas = {
        --   ["https://json.schemastore.org/github-workflow.json"] = "/.github/workflows/*.yml",
        --   ["https://json.schemastore.org/github-action.json"] = "/.github/action.yml",
        --   ["https://www.schemastore.org/prometheus.json"] = "/prometheus.yml",
        --   ["https://raw.githubusercontent.com/compose-spec/compose-spec/master/schema/compose-spec.json"] =
        --   "/docker-compose.yml",
        --   ["https://raw.githubusercontent.com/composer/xdebug-handler/2/res/schema.json"] = "/composer.json",
        -- },
      },
    }
  },
  -- volar = {
  --   filetypes = {
  --     "vue"
  --   },
  -- },
  ts_ls = {
    filetypes = {
      "typescript",
      "javascript",
      "javascriptreact",
      "typescriptreact",
      -- "vue"
    },
  },
  jsonls = {
    settings = {
      json = {
        schemas = schemastore.json.schemas(),
        validate = { enable = true },
      },
    }
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
