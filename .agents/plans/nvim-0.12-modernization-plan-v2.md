# Neovim 0.12 Modernization Plan v2

Date: 2026-05-17
Scope: `nvim/.config/nvim`
Status: planning only, no config changes made yet

## Goals

- Fix the current startup errors.
- Remove plugins that are broken, duplicated, unused, or replaced well by Neovim 0.12 built-ins.
- Keep behavior where native Neovim does not provide an equivalent.
- Make remaining plugin usage match current plugin APIs.

## Direct Answers

### Native LSP vs `nvim-lspconfig`

Neovim 0.12 has the native LSP client and native setup API:

- `vim.lsp.config()`
- `vim.lsp.enable()`
- global default mappings like `gra`, `grn`, `grr`, `gri`, `grt`, `gO`, `K`

But this Neovim install does not ship server config files under `/usr/share/nvim/runtime/lsp`. Runtime checks show server configs such as `ts_ls.lua` and `lua_ls.lua` currently come from:

- `~/.local/share/nvim/lazy/nvim-lspconfig/lsp/*.lua`

So:

- `require("lspconfig")[server].setup(...)` is stale/deprecated and should be removed.
- `nvim-lspconfig` itself is still useful as a server-default database unless we manually define every server's `cmd`, `filetypes`, root detection, special commands, and handlers.
- A later maximum-lean pass can remove `nvim-lspconfig`, but only after replacing its server defaults in local config.

### Native Comments vs `Comment.nvim`

Neovim 0.12 has native commenting:

- `gc{motion}`
- `gcc`
- visual `gc`
- operator-pending `gc` text object for comment blocks
- Treesitter-aware `commentstring` lookup when parsers and injections are available

This can replace your explicit custom mappings that only forward to `gcc` and `gc`:

- `<C-c>` in normal mode
- `<C-c>` in visual mode
- `<leader>/` in normal mode
- `<leader>/` in visual mode

It does not fully replace all `Comment.nvim` behavior:

- No separate built-in `gb` / `gbc` block-comment operator.
- No built-in `gco`, `gcO`, `gcA` insert-comment helpers.
- No Comment.nvim hook system.

Recommended first pass: remove `Comment.nvim` and re-add only the custom alias bindings to native `gcc/gc`. If block-comment helpers are important, keep `Comment.nvim` or add a small custom implementation later.
Feedback: Block-comments are important actually.

## Current Breakages

### Treesitter API mismatch

`lazy-lock.json` has:

- `nvim-treesitter` on `main`

But `lua/plugins/treesitter.lua` still uses:

- `require("nvim-treesitter.configs").setup(...)`

The installed `nvim-treesitter` README says the `main` branch is a full incompatible rewrite. It no longer provides the old `nvim-treesitter.configs` module.

Directly broken because they also require the old module:

- `nvim-treesitter/nvim-treesitter-textobjects`
- `HiPhish/nvim-ts-rainbow2`

### Parser/query skew

Opening a Lua file headlessly produced a Treesitter query error for the Lua query field `operator`.

Runtime parser order shows:

1. `~/.local/share/nvim/lazy/nvim-treesitter/parser/lua.so`
2. `/usr/share/nvim/runtime/parser/lua.so`

The parser under the lazy plugin shadows Neovim's packaged parser and appears stale relative to the active queries.

### Deprecated API usage

Found usages to modernize:

- `vim.diagnostic.goto_prev()` -> `vim.diagnostic.jump({ count = -1, float = true })`
- `vim.diagnostic.goto_next()` -> `vim.diagnostic.jump({ count = 1, float = true })`
- `vim.lsp.buf_get_clients()` -> `vim.lsp.get_clients({ bufnr = 0 })`
- `require("lspconfig")[server].setup(...)` -> `vim.lsp.config(...)` + `vim.lsp.enable(...)`
- `vim.api.nvim_exec(...)` for filetype autocmd -> `vim.filetype.add(...)`
- `nvim_buf_set_option()` -> `vim.bo[buf]...`
- `nvim_get_option()` -> `vim.o...`
- `vim.fn.sign_define(...)` diagnostic signs -> `vim.diagnostic.config({ signs = { text = ... } })`
- `LuaSnip` lazy spec uses `run = ...`; lazy.nvim uses `build = ...`

`init.lua` currently disables deprecation warnings globally:

- `vim.deprecate = function() end`

This should be removed after the config is cleaned up.

## Plugin Audit

### Remove or Replace With Native

Good first-pass removals:

- `numToStr/Comment.nvim`
  - Replace configured aliases with native `gcc/gc`.
  - Loses `gb`, `gbc`, `gco`, `gcO`, `gcA` unless reimplemented or plugin is kept.

- `nathom/filetype.nvim`
  - Replace Blade override with `vim.filetype.add({ pattern = { [".*%.blade%.php"] = "blade" } })`.

- `nvim-treesitter/playground`
  - Replace with built-in `:InspectTree` / `vim.treesitter.inspect_tree()`.

- `jessarcher/vim-heritage`
  - Replace with native `:write ++p` or the documented `BufWritePre` mkdir autocmd.

- `farmergreg/vim-lastplace`
  - Replace with a small native `BufReadPost` autocmd.

- `sheerun/vim-polyglot`
  - Remove unless a specific non-Treesitter syntax regression is found.
  - It is broad and can conflict with modern filetype/Treesitter behavior.

- `HiPhish/nvim-ts-rainbow2`
  - Broken against current `nvim-treesitter main`.
  - Remove in first pass.

- `nvim-treesitter/nvim-treesitter-textobjects`
  - Broken against current `nvim-treesitter main`.
  - Remove in first pass.

- `JoosepAlviste/nvim-ts-context-commentstring`
  - Remove if native Treesitter `bo.commentstring` metadata plus native commenting covers Blade/JSX/Vue cases.
  - Keep only if embedded-language comments regress.

- `mskelton/termicons.nvim`
  - No config usage found.
  - Also contributes lazy-rocks paths to Lua module search.
  - Remove unless there is a concrete UI feature depending on it.

- `cmp-nvim-lsp`
  - Remove after switching LSP capabilities to `require("blink.cmp").get_lsp_capabilities()`.

- `cmp_luasnip`
  - Remove after consolidating completion on `blink.cmp`.

- `nvim-cmp`
  - Currently pulled in for `blade-nav.nvim`.
  - Running both `blink.cmp` and `nvim-cmp` is inconsistent.
  - Remove unless Blade route/view completion from `blade-nav` is mandatory.
  - `blade-nav` keeps `gf` navigation without cmp; its cmp source returns early if `cmp` is missing.

- `dropbar.lua`
  - File only returns commented-out config. Remove the file.

- `noice.lua`
  - File returns `{}` and only contains commented config with stale `nvim-cmp` references. Remove the file.

### Keep For Now

These do not have exact native equivalents or are still useful:

- `folke/lazy.nvim`
  - Neovim 0.12 has `vim.pack`, but replacing lazy.nvim would lose lockfile/lazy-loading conventions and is outside the startup-fix scope.

- `neovim/nvim-lspconfig`
  - Keep as config provider, but stop using deprecated `require("lspconfig")`.

- `williamboman/mason.nvim`
- `williamboman/mason-lspconfig.nvim`
- `WhoIsSethDaniel/mason-tool-installer.nvim`
  - Native LSP does not install servers/tools.

- `saghen/blink.cmp`
  - Native LSP omnifunc exists, but this config expects modern popup completion and snippets.

- `L3MON4D3/LuaSnip`
- `rafamadriz/friendly-snippets`
- `onecentlin/laravel-blade-snippets-vscode`
  - Native snippets are not an exact replacement for this setup and custom snippets.

- `nvim-telescope/telescope.nvim`
- `telescope-fzf-native.nvim`
- `telescope-ui-select.nvim`
  - Neovim has `vim.ui.select`, `:find`, `:grep`, and `:oldfiles`, but no equivalent full fuzzy picker stack.

- `nvim-neo-tree/neo-tree.nvim`
- `MunifTanjim/nui.nvim`
- `nvim-lua/plenary.nvim`
  - Native netrw exists, but this config uses Neo-tree behavior and bindings.

- `3rd/image.nvim`
  - Optional Neo-tree preview dependency. Remove only if image preview is not used.(feedback: image-preview is not used)

- `lewis6991/gitsigns.nvim`
  - Native diff/git features do not replace hunk signs, staging, and blame bindings.

- `stevearc/conform.nvim`
- `mfussenegger/nvim-lint`
  - Native LSP format/diagnostics do not cover all external formatters/linters configured here.

- `lukas-reineke/indent-blankline.nvim`
  - No exact native indent guide feature.

- `nvim-lualine/lualine.nvim`
- `akinsho/bufferline.nvim`
- `goolord/alpha-nvim`
- `olimorris/onedarkpro.nvim`
  - UI choices, not native-equivalent cleanup targets.

- `folke/which-key.nvim`
  - Native map descriptions exist, but not the popup UX.

- `folke/snacks.nvim`
  - Currently only notifier is configured. Keep until notification behavior is confirmed.

- `j-hui/fidget.nvim`
  - Neovim 0.12 has progress status APIs, but not an equivalent UI display by itself.

- `folke/twilight.nvim`
- `folke/zen-mode.nvim`
  - No exact native equivalent.

- `windwp/nvim-autopairs`
  - No exact native pair insertion.

- `tpope/vim-surround`
  - No exact native surround editing.

- `tpope/vim-repeat`
  - Still useful for repeat support with older Vim plugins.

- `tpope/vim-unimpaired`
  - Native has some bracket motions, but not the whole plugin behavior.

- `christoomey/vim-tmux-navigator`
  - No native tmux integration.

- `AndrewRadev/splitjoin.vim`
  - No exact native split/join transform behavior.

- `whatyouhide/vim-textobj-xmlattr`
- `kana/vim-textobj-user`
  - No exact native XML/HTML attribute textobject.

- `vim-blade`
  - Candidate for later removal if the custom Blade parser/queries fully cover highlighting and filetype needs.
  - Do not remove in the first pass without Blade test files.

- `ricardoramirezr/blade-nav.nvim`
  - Keep for `gf` Blade navigation.
  - Its nvim-cmp completion integration becomes inactive if `nvim-cmp` is removed.

### Review After First Pass

Optional deeper cleanup:

- `numToStr/FTerm.nvim`
  - Native terminal exists. A small Lua floating terminal can replace the plugin, but exact toggle behavior needs local code.(feedback: I think we should drop this plugin in favour of tmux display-popup command (falling back to native neovim terminal if not in tmux))

- `famiu/bufdelete.nvim`
  - Native `:bdelete` exists but can close windows. Plugin preserves layout more nicely.

- `karb94/neoscroll.nvim`
  - Native scrolling works but is not animated.

- `sickill/vim-pasta`
  - Neovim has bracketed paste and sane paste behavior, but this plugin may still affect indentation edge cases.

- `nvim-web-devicons` and `mini.icons`
  - Both icon providers are present.
  - `which-key` uses `mini.icons`; Neo-tree/bufferline/lualine/Telescope use `nvim-web-devicons`.
  - Possible to standardize later, but not required for correctness.

## Planned File Changes

### `init.lua`

- Remove `vim.deprecate = function() end` after replacing deprecated usage.
- Keep lazy.nvim for now.

### `lua/vim/options.lua`

- Replace Vimscript-style `set` calls with direct `vim.opt` assignments where straightforward.
- Replace the Blade `nvim_exec` autocmd with `vim.filetype.add()`.
- Keep folding options using `vim.treesitter.foldexpr()`.

### `lua/vim/autocmds.lua`

- Remove manual TSX filetype/LSP-start autocmd unless testing shows Neovim 0.12 does not detect TSX.
- Add native last-place autocmd to replace `vim-lastplace`.
- Add optional native parent-directory autocmd if replacing `vim-heritage`.
- Keep yank highlight and VSCode words loading.

### `lua/vim/keymaps.lua`

- Replace deprecated diagnostic jumps with `vim.diagnostic.jump`.
- Keep save/window/fold/terminal-exit mappings.
- Add native comment aliases if removing `Comment.nvim`.

### `lua/user/lsp/on_attach.lua`

- Set diagnostic config once, not on every LSP attach.
- Use `vim.diagnostic.config({ signs = { text = ... } })`.
- Scope LSP keymaps to `event.buf`.
- Remove duplicate LSP mappings where native defaults are good enough, or keep the Telescope-flavored mappings explicitly.
- Replace deprecated diagnostic jumps.

### `lua/plugins/lspconfig.lua`

- Keep `neovim/nvim-lspconfig`, but use it only as runtime config provider.
- Replace `require("lspconfig")[server_name].setup(server)` with:
  - merge local server settings
  - `vim.lsp.config(server_name, server)`
  - `vim.lsp.enable(server_name)`
- Use `require("blink.cmp").get_lsp_capabilities()`.
- Remove `cmp-nvim-lsp`.
- Configure `mason-lspconfig` with `automatic_enable = false` so Mason does not enable servers before local overrides are applied.

### `lua/user/lsp/servers.lua`

- Keep local server customizations.
- Do not manually copy full server defaults from `nvim-lspconfig` in the first pass.
- Later, if removing `nvim-lspconfig`, each server here must gain full `cmd`, root detection, and command/handler definitions.

### `lua/plugins/treesitter.lua`

- Replace old `require("nvim-treesitter.configs").setup(...)`.
- Use current `require("nvim-treesitter").setup(...)`.
- Keep `nvim-treesitter` as `lazy = false`.
- Add a `FileType` autocmd to call `vim.treesitter.start()` for supported filetypes.
- Remove old companion plugins that require `nvim-treesitter.configs`.
- Replace playground with native `:InspectTree`.
- Keep custom Blade parser registration using current parser-table style.

### `lua/plugins/comment.lua`

- Remove file if using native comments.
- Re-add aliases in `lua/vim/keymaps.lua`.

### `lua/plugins/completions.lua` and `lua/plugins/snippets.lua`

- Consolidate duplicate `LuaSnip` declarations into one file.
- Use `build = "make install_jsregexp"`.
- Remove `cmp_luasnip`.
- Remove unused `_G.has_words_before`.
- Keep local snipmate snippets and VSCode/friendly snippets.
- Decide how to handle `blade-nav` completion:
  - lean option: remove `nvim-cmp` and accept losing Blade route/view completion items
  - exact option: keep `nvim-cmp` only for `blade-nav`, or write a blink.cmp source later

### `lua/plugins/init.lua`

- Remove or replace first-pass cleanup plugins listed above.
- Fix `dependecies` typo if `termicons.nvim` is kept; otherwise remove `termicons.nvim`.
- Keep plugin list grouped and explicit.

### `lua/plugins/lualine.lua`

- Replace `vim.lsp.buf_get_clients()` with `vim.lsp.get_clients({ bufnr = 0 })`.

### `lua/plugins/which-key.lua`

- Update `which-key.register(...)` to the current `which-key.add(...)` style if the installed plugin warns.

### `lua/user/utils.lua`

- Replace deprecated option APIs:
  - `api.nvim_buf_set_option(buf, "bufhidden", "wipe")` -> `vim.bo[buf].bufhidden = "wipe"`
  - `api.nvim_get_option("columns")` -> `vim.o.columns`
  - `api.nvim_get_option("lines")` -> `vim.o.lines`
- Leave JSON mutation logic alone unless it becomes part of a dedicated cleanup.

### `lazy-lock.json`

- Update through lazy.nvim after plugin spec changes.
- Remove lock entries for removed plugins after running sync/clean.

### `pocman/.config/pocman/arch.toml`

- Add `tree-sitter-cli` if keeping `nvim-treesitter` on `main`.
- The installed `nvim-treesitter` README lists it as a requirement.

## Local State Cleanup

After plan approval and config patching:

- Move stale parsers aside rather than deleting:
  - from `~/.local/share/nvim/lazy/nvim-treesitter/parser`
  - to `~/.local/share/nvim/lazy/nvim-treesitter/parser.backup-2026-05-17`
- Reinstall/update parsers only after `tree-sitter-cli` exists:
  - `nvim --headless "+TSUpdate" +qa`

If `tree-sitter-cli` is unavailable, prefer Neovim packaged parsers temporarily and defer parser installation.

## Bindings To Re-add Or Decide On

### Re-add if removing `Comment.nvim`

Native comments already provide `gcc`, `gc{motion}`, and visual `gc`. Re-add only your aliases:

```lua
vim.keymap.set("n", "<C-c>", "gcc", { remap = true, desc = "Comment line" })
vim.keymap.set("x", "<C-c>", "gc", { remap = true, desc = "Comment selection" })
vim.keymap.set("n", "<leader>/", "gcc", { remap = true, desc = "Comment line" })
vim.keymap.set("x", "<leader>/", "gc", { remap = true, desc = "Comment selection" })
```

Lost unless kept or reimplemented:

- `gbc`: block-comment current line from Comment.nvim
- `gb{motion}`: block-comment motion from Comment.nvim
- visual `gb`: block-comment selection from Comment.nvim
- `gco`: insert comment below from Comment.nvim
- `gcO`: insert comment above from Comment.nvim
- `gcA`: insert comment at end of line from Comment.nvim

### Re-add if removing `nvim-treesitter-textobjects`

Current mappings that will disappear:

- `if`: `@function.inner`
- `af`: `@function.outer`
- `ia`: `@parameter.inner`
- `aa`: `@parameter.outer`

These are not native Neovim textobjects. Options:

- Accept losing them in first pass.
- Re-add later with a current Treesitter textobject plugin.
- Implement small custom textobjects only for the languages you use most.

### Re-add if replacing `vim-lastplace`

Equivalent native autocmd:

```lua
vim.api.nvim_create_autocmd("BufReadPost", {
  callback = function(event)
    local mark = vim.api.nvim_buf_get_mark(event.buf, [["]])
    local line_count = vim.api.nvim_buf_line_count(event.buf)
    if mark[1] > 0 and mark[1] <= line_count then
      pcall(vim.api.nvim_win_set_cursor, 0, mark)
    end
  end,
})
```

### Re-add if replacing `vim-heritage`

Native `:write ++p` works manually. To make plain `:write` create parent directories:

```lua
vim.api.nvim_create_autocmd({ "BufWritePre", "FileWritePre" }, {
  callback = function(event)
    if event.match:match("://") then
      return
    end
    vim.fn.mkdir(vim.fn.fnamemodify(event.match, ":p:h"), "p")
  end,
})
```

### Re-add if removing `vim-visual-star-search`

Visual `*` is not a full native equivalent. Add a small mapping later if you rely on visual-star search.

### Re-add if replacing `FTerm.nvim`

Current bindings:

- normal `<A-t>` toggles floating terminal
- terminal `<A-t>` exits terminal mode and toggles floating terminal

Native terminal can do this, but it needs a small custom floating-terminal module. Do not remove FTerm in the first pass unless replacing these bindings at the same time.

### Re-add if removing `bufdelete.nvim`

Current binding:

- `<leader>q`: `:Bdelete`

Native `:bdelete` is not the same because it may close windows. Keep plugin or replace with a custom buffer-delete helper before removing.

### LSP mappings to keep or intentionally drop

Neovim 0.12 global defaults already provide:

- `gra`: code action
- `grn`: rename
- `grr`: references
- `gri`: implementation
- `grt`: type definition
- `gO`: document symbols
- `K`: hover, unless overridden

Your current custom mappings are more mnemonic and often Telescope-backed:

- `gd`: Telescope definitions
- `gD`: declaration
- `gr`: Telescope references
- `gI`: Telescope implementations
- `<leader>d`: diagnostic float
- `<leader>D`: Telescope type definitions
- `<leader>ds`: Telescope document symbols
- `<leader>ws`: Telescope workspace symbols
- `<leader>rn`: rename
- `<leader>ca`: code action
- `K`: hover
- `<leader>th`: toggle inlay hints

Recommended first pass: keep these mappings but make them buffer-local and remove duplicate global diagnostic mappings.

## Verification Plan

Run after implementation:

1. `nvim --headless +qa`
2. `nvim --headless nvim/.config/nvim/init.lua +qa`
3. `nvim --headless "+lua require('nvim-treesitter')" +qa`
4. `nvim --headless "+lua print(vim.inspect(vim.api.nvim_get_runtime_file('parser/lua.so', true)))" +qa`
5. `nvim --headless "+Neotree filesystem reveal right" +qa`
6. `nvim --headless "+checkhealth vim.treesitter" "+checkhealth vim.lsp" "+checkhealth lazy" +qa`
7. Open representative files manually:
   - Lua
   - PHP
   - Blade
   - TSX
   - Vue
   - Markdown

Expected result:

- No `nvim-treesitter.configs` error.
- No Lua Treesitter query/parser mismatch.
- Neo-tree opens without sourcing `nvim-ts-rainbow2`.
- Native `gcc`, visual `gc`, `<C-c>`, and `<leader>/` comments work.
- LSP servers attach through `vim.lsp.enable`.
- No Neovim 0.12 deprecation warnings from our config.

## Suggested Execution Order

1. Fix Treesitter and stale parser shadowing.
2. Replace diagnostic/LSP deprecated APIs.
3. Remove native-replaced plugins and re-add bindings.
4. Consolidate completion/snippet config.
5. Clean lockfile and lazy plugin directory.
6. Run verification.
7. Decide on optional deeper removals: FTerm, bufdelete, nvim-lspconfig, vim-blade, icon provider duplication.
