local u = require("user.utils")
-- [[ Basic Keymaps ]]
vim.opt.hlsearch = true
u.map('n', '<Esc>', '<cmd>nohlsearch<CR>')
u.map('n', '<C-s>', '<cmd>w<cr>')
u.map('n', '<leader>w', '<C-s>', { remap = true })

-- Diagnostic keymaps
u.map('n', '[d', vim.diagnostic.goto_prev, { desc = 'Go to previous [D]iagnostic message' })
u.map('n', ']d', vim.diagnostic.goto_next, { desc = 'Go to next [D]iagnostic message' })
u.map('n', '<leader>e', vim.diagnostic.open_float, { desc = 'Show diagnostic [E]rror messages' })
u.map('n', '<leader>q', vim.diagnostic.setloclist, { desc = 'Open diagnostic [Q]uickfix list' })

-- Exit terminal mode in the builtin terminal with a shortcut that is a bit easier
-- for people to discover. Otherwise, you normally need to press <C-\><C-n>, which
-- is not what someone will guess without a bit more experience.
--
-- NOTE: This won't work in all terminal emulators/tmux/etc. Try your own mapping
-- or just use <C-\><C-n> to exit terminal mode
u.map('t', '<Esc><Esc>', '<C-\\><C-n>', { desc = 'Exit terminal mode' })

--  Use CTRL+<hjkl> to switch between windows
--  See `:help wincmd` for a list of all window commands
u.map('n', '<C-h>', '<C-w><C-h>', { desc = 'Move focus to the left window' })
u.map('n', '<C-l>', '<C-w><C-l>', { desc = 'Move focus to the right window' })
u.map('n', '<C-j>', '<C-w><C-j>', { desc = 'Move focus to the lower window' })
u.map('n', '<C-k>', '<C-w><C-k>', { desc = 'Move focus to the upper window' })

--Toggle Folding --
u.map('n', '<leader>fb', "za", {remap = true, desc = "[F]old [B]lock (toggle)"})
u.map('n', '<leader>fa', "zM", {remap = true, desc = "[F]old [A]ll Blocks"})
