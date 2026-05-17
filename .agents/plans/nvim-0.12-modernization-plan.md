# Neovim 0.12 Modernization Plan

Superseded by: `.agents/plans/nvim-0.12-modernization-plan-v2.md`

Date: 2026-05-17
Scope: `nvim/.config/nvim`

## Current Findings

The startup error is caused by an API mismatch:

- `lazy-lock.json` has `nvim-treesitter` on the rewritten `main` branch.
- The config in `lua/plugins/treesitter.lua` still uses the old `require("nvim-treesitter.configs").setup(...)` API.
- `nvim-treesitter-textobjects` and `nvim-ts-rainbow2` also load `nvim-treesitter.configs`, so they fail as soon as their plugin files are sourced.

There is a second Treesitter issue:

- A stale parser directory exists at `~/.local/share/nvim/lazy/nvim-treesitter/parser`.
- It shadows Neovim's packaged parsers, for example `lua.so`.
- Opening a Lua file currently errors with an invalid `operator` field in the Lua highlight query, which indicates parser/query version skew.

Neovim 0.12.2 docs and installed plugin docs point to several leaner built-in paths:

- Use built-in Treesitter highlighting with `vim.treesitter.start()`.
- Use built-in `:InspectTree` / `vim.treesitter.inspect_tree()` instead of `nvim-treesitter/playground`.
- Use built-in filetype detection through `vim.filetype.add()` instead of `filetype.nvim`.
- Use `vim.diagnostic.jump()` instead of deprecated `vim.diagnostic.goto_next()` / `goto_prev()`.
- Use `vim.lsp.config()` and `vim.lsp.enable()` instead of `require("lspconfig")[server].setup(...)`.

## Proposed Direction

Modernize toward Neovim 0.12 APIs instead of pinning old plugin branches.

This intentionally removes or replaces old plugin behavior where Neovim now has a native feature. The main tradeoff is that old Treesitter textobject mappings (`if`, `af`, `ia`, `aa`) are not built into Neovim. I will remove the broken textobjects plugin first; if those mappings are still important, add back a maintained textobject plugin in a separate follow-up.

## Planned File Changes

### 1. `nvim/.config/nvim/lua/plugins/treesitter.lua`

- Replace old `require("nvim-treesitter.configs").setup(...)` with the new `require("nvim-treesitter").setup(...)` API.
- Mark `nvim-treesitter` as `lazy = false`, matching the current plugin README.
- Remove dependencies that require the old configs API:
  - `nvim-treesitter/nvim-treesitter-textobjects`
  - `HiPhish/nvim-ts-rainbow2`
  - `JoosepAlviste/nvim-ts-context-commentstring` if it remains unused after the native commentstring path is tested
- Remove `nvim-treesitter/playground`; Neovim 0.12 has `:InspectTree`.
- Add a `FileType` autocmd that starts Treesitter highlighting with `vim.treesitter.start()` for configured languages when a parser is available.
- Keep Treesitter folding through the existing `vim.treesitter.foldexpr()`.
- Register the custom Blade parser using the new parser table style shown in the installed `nvim-treesitter` README.

### 2. `nvim/.config/nvim/lua/vim/options.lua`

- Remove the `vim.deprecate = function() end` suppression from `init.lua` after actual deprecations are fixed.
- Replace the Blade `nvim_exec` autocommand with `vim.filetype.add()`.
- Keep normal editor options, but avoid Vimscript `set` calls where direct `vim.opt` assignments are clearer.

### 3. `nvim/.config/nvim/lua/vim/autocmds.lua`

- Remove the manual TSX filetype/LSP-start autocmd unless testing shows Neovim 0.12 does not detect TSX correctly.
- Move filetype-specific setup to `vim.filetype.add()` or normal `FileType` autocmds.

### 4. `nvim/.config/nvim/lua/vim/keymaps.lua`

- Replace deprecated diagnostic mappings:
  - `[d` -> `vim.diagnostic.jump({ count = -1, float = true })`
  - `]d` -> `vim.diagnostic.jump({ count = 1, float = true })`

### 5. `nvim/.config/nvim/lua/user/lsp/on_attach.lua`

- Move global diagnostic configuration out of `LspAttach` so it is set once.
- Replace `vim.fn.sign_define(...)` with `vim.diagnostic.config({ signs = { text = ... } })`.
- Replace deprecated diagnostic jump mappings here as well.
- Add `buffer = event.buf` to LSP keymaps so mappings are scoped to attached buffers.

### 6. `nvim/.config/nvim/lua/plugins/lspconfig.lua`

- Use `require("blink.cmp").get_lsp_capabilities()` instead of the non-current `blink_cmp.capabilities()` check.
- Configure each server with `vim.lsp.config(server_name, server_config)`.
- Enable each server with `vim.lsp.enable(server_name)`.
- Configure `mason-lspconfig` with `automatic_enable = false` so customized configs are not bypassed or double-enabled.

### 7. `nvim/.config/nvim/lua/plugins/init.lua`

- Remove `nathom/filetype.nvim`.
- Remove `sheerun/vim-polyglot` unless a specific language regression appears in testing.
- Fix typo `dependecies` -> `dependencies` for `termicons.nvim`, or remove `termicons.nvim` if it is unused after checking UI/plugin usage.
- Review stale small Vim plugins:
  - Keep `vim-sleuth`, `vim-surround`, `vim-repeat`, `vim-unimpaired`, `vim-tmux-navigator` unless there is a concrete replacement or breakage.
  - Consider replacing `vim-lastplace` with a small native autocmd.
  - Consider replacing `vim-heritage` with `:write ++p` workflow or a small native write autocmd.

### 8. `nvim/.config/nvim/lua/plugins/completions.lua` and `snippets.lua`

- Consolidate duplicate LuaSnip specs. LuaSnip is currently declared in both files.
- Replace lazy.nvim `run = "make install_jsregexp"` with `build = "make install_jsregexp"`.
- Remove the unused global `_G.has_words_before` helper if it is no longer referenced.
- Keep Blade and project snippets loading after consolidation.

### 9. `nvim/.config/nvim/lua/plugins/lualine.lua`

- Replace deprecated `vim.lsp.buf_get_clients()` with `vim.lsp.get_clients({ bufnr = 0 })`.

### 10. `nvim/.config/nvim/lua/plugins/which-key.lua`

- Update old `require("which-key").register(...)` usage to current `which-key.add(...)` style if the installed plugin warns during verification.

### 11. `nvim/.config/nvim/lua/user/utils.lua`

- Replace deprecated low-level APIs:
  - `api.nvim_buf_set_option(buf, ...)` -> `vim.bo[buf]...`
  - `api.nvim_get_option("columns")` -> `vim.o.columns`
  - `api.nvim_get_option("lines")` -> `vim.o.lines`
- Keep JSON edits untouched for now unless they are directly implicated in startup errors.

### 12. `pocman/.config/pocman/arch.toml`

- Add `tree-sitter-cli` to CLI packages if we keep `nvim-treesitter` on the rewritten `main` branch.
- Reason: the installed `nvim-treesitter` README lists the CLI as a requirement for parser installation/update.

## Local State Cleanup

This part touches files outside the dotfiles repo and should be done only after config changes are reviewed:

- Move, not delete, the stale parser directory:
  - from `~/.local/share/nvim/lazy/nvim-treesitter/parser`
  - to `~/.local/share/nvim/lazy/nvim-treesitter/parser.backup-2026-05-17`
- Then run a parser update after `tree-sitter-cli` is available:
  - `nvim --headless "+TSUpdate" +qa`

If network or package installation is not available, the fallback is to keep only Neovim-packaged parsers active and defer language parser updates.

## Verification Plan

Run these after implementation:

1. `nvim --headless +qa`
2. `nvim --headless nvim/.config/nvim/init.lua +qa`
3. `nvim --headless "+lua require('nvim-treesitter')" +qa`
4. `nvim --headless "+lua print(vim.inspect(vim.api.nvim_get_runtime_file('parser/lua.so', true)))" +qa`
5. `nvim --headless "+Neotree filesystem reveal right" +qa`
6. `nvim --headless "+checkhealth vim.treesitter" "+checkhealth lsp" "+checkhealth lazy" +qa`

Expected result:

- No `nvim-treesitter.configs` error.
- No Lua Treesitter query/parser mismatch when opening Lua files.
- Neo-tree opens without sourcing `nvim-ts-rainbow2`.
- No Neovim 0.12 deprecation warnings from our own config.

## Deferred Follow-ups

- Replace removed Treesitter textobjects with a maintained alternative if those mappings are important.
- Revisit Blade highlighting and injections after parser update, because this config has both `queries/` and `after/queries/` copies.
- Consider trimming duplicate or unused UI plugins after startup stability is restored.
