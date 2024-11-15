-- [IMPORTANT FOR NIXOS]
-- If using the lsp name does not match with nixpkg name then use nixpkg_name e.g: `nixpkg_name = "lua54Packages.lua-lsp"`,
-- after adding a new server run :NLSPInstall
-- Then update your system using nixos

return {
  gopls = {
    nixpkg_name = "gopls",
    settings = {
      gopls = {
        completeUnimported = true,
        usePlaceholders = true,
        analyses = {
          unusedparams = true,
        },
      },
    },
  },
  nil_ls = { nixpkg_name = "nil" }, -- LSP for Nix
  tailwindcss = {
    nixpkg_name = "tailwindcss-language-server",
    filetypes = { "html", "css", "javascript", "typescript", "blade", "typescriptreact", "javascriptreact", "vue", "svelte" }
  },
  volar = {
    nixpkg_name = "nodePackages.volar",
    filetypes = { "vue" },
  },
  ts_ls = {
    nixpkg_name = "nodePackages.typescript-language-server",
    binary = "typescript-language-server",
    filetypes = {
      "typescript",
      "javascript",
      "javascriptreact",
      "typescriptreact",
      -- "vue"
    },
  },
  -- LSPs for PHP
  psalm = {
    nixpkg_name = "php83Packages.psalm",
  },
  intelephense = {
    nixpkg_name = "nodePackages.intelephense",
  },
  phpactor = { nixpkg_name = "phpactor", filetypes = { "php", "blade" } },
  -- LSPs for Lua
  lua_ls = {
    nixpkg_name = "lua52Packages.lua-lsp",
    binary = "lua-language-server",
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
