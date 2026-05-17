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

vim.api.nvim_create_autocmd("BufReadPost", {
  desc = "Restore cursor to the last known position",
  group = vim.api.nvim_create_augroup("user-last-place", { clear = true }),
  callback = function(event)
    local mark = vim.api.nvim_buf_get_mark(event.buf, '"')
    local line_count = vim.api.nvim_buf_line_count(event.buf)

    if mark[1] > 0 and mark[1] <= line_count then
      pcall(vim.api.nvim_win_set_cursor, 0, mark)
    end
  end,
})

vim.api.nvim_create_autocmd({ "BufWritePre", "FileWritePre" }, {
  desc = "Create missing parent directories before writing files",
  group = vim.api.nvim_create_augroup("user-auto-mkdir", { clear = true }),
  callback = function(event)
    if event.match:match("://") then
      return
    end

    vim.fn.mkdir(vim.fn.fnamemodify(event.match, ":p:h"), "p")
  end,
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
