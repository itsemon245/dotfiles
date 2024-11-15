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
