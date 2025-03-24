-- [[ Basic Autocommands ]]
--  See `:help lua-guide-autocommands`

-- Highlight when yanking (copying) text
--  Try it with `yap` in normal mode
--  See `:help vim.highlight.on_yank()`
vim.api.nvim_create_autocmd('TextYankPost', {
  desc = 'Highlight when yanking (copying) text',
  group = vim.api.nvim_create_augroup('kickstart-highlight-yank', { clear = true }),
  callback = function()
    vim.highlight.on_yank()
  end,
})

-- vim.api.nvim_create_autocmd("InsertCharPre", {
--   pattern = "*.snippets",
--   callback = function()
--     vim.keymap.set("i", "<CR>", function()
--       local line = vim.api.nvim_get_current_line()
--
--       -- Check if the current line starts with "snippet"
--       if line:match("^snippet") then
--         return vim.api.nvim_replace_termcodes("<CR><Tab>", true, false, true)
--       end
--     end, { buffer = true, expr = true })
--   end,
-- })

-- local current_file = ""
-- vim.api.nvim_create_autocmd({ "BufEnter", "BufWinEnter" }, {
--   pattern = { "*.blade.php" },
--   callback = function()
--     current_file = vim.fn.expand("%:p")
--   end
-- })
-- vim.api.nvim_create_autocmd({ "BufWritePre" }, {
--   pattern = { "*.blade.php" },
--   -- command = ("!blade-formatter -w " .. current_file)
--   callback = function()
--     vim.api.nvim_command("!blade-formatter -w " .. current_file)
--   end
-- })

-- Ensure TSX files are properly detected
vim.api.nvim_create_autocmd({"BufRead", "BufNewFile"}, {
  pattern = {"*.tsx"},
  callback = function()
    vim.bo.filetype = "typescriptreact"
    -- Force LSP to attach
    vim.cmd("LspStart")
  end
})

-- Fix for TreeSitter TSX query error
vim.api.nvim_create_autocmd({"VimEnter"}, {
  callback = function()
    -- Create directory if it doesn't exist
    local query_dir = vim.fn.stdpath("config") .. "/after/queries/tsx"
    vim.fn.mkdir(query_dir, "p")
    
    -- Create a fixed highlights.scm file
    local highlights_file = query_dir .. "/highlights.scm"
    if not vim.loop.fs_stat(highlights_file) then
      local file = io.open(highlights_file, "w")
      if file then
        -- This is a corrected version that fixes the problematic pattern
        file:write([[
;; extends
(jsx_element
  open_tag: (jsx_opening_element) @tag)

(jsx_element
  close_tag: (jsx_closing_element) @tag)

(jsx_self_closing_element) @tag

(jsx_attribute
  (property_identifier) @tag.attribute)

(jsx_text) @none

(jsx_expression) @expression
]])
        file:close()
        print("Created fixed TSX query file for proper highlighting")
      end
    end
  end
})

local utils = require("user.utils")

-- Load VSCode user words on first buffer
vim.api.nvim_create_autocmd("BufEnter", {
  pattern = "*",
  callback = function()
    if not vim.g.vscode_words_loaded then
      vim.g.vscode_words_loaded = true
      utils.load_vscode_user_words()
    end
  end,
  group = vim.api.nvim_create_augroup("LoadVSCodeWords", { clear = true })
})
