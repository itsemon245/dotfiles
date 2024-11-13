-- If using the lsp name does not match with nixpkg name then use nixpkg_name e.g: `nixpkg_name = "lua54Packages.lua-lsp"`,
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
  ts_ls = {
    nixpkg_name = "nodePackages.typescript-language-server",
    filetypes = { "typescript", "javascript", "javascriptreact", "typescriptreact", "vue" },
  },
  -- phpactor = {},
  psalm = {}, -- LSP for PHP
  lua_ls = {
    nixpkg_name = "lua54Packages.lua-lsp",
    settings = {
      Lua = {
        completion = {
          callSnippet = 'Replace',
        },
        -- You can toggle below to ignore Lua_LS's noisy `missing-fields` warnings
        -- diagnostics = { disable = { 'missing-fields' } },
      },
    },
  },
}
