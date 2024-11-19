local map = require('user.utils').map
-- Gitsigns keymaps
map('n', ']h', ':Gitsigns next_hunk<CR>', { noremap = true, desc = 'Next [H]unk' })
map('n', '[h', ':Gitsigns prev_hunk<CR>', { noremap = true, desc = 'Prev [H]unk' })
map('n', '<leader>hs', ':Gitsigns stage_hunk<CR>', { noremap = true, desc = 'Stage hunk' })
map('n', '<leader>hS', ':Gitsigns stage_buffer<CR>', { noremap = true, desc = 'Stage buffer' })
map('n', '<leader>hu', ':Gitsigns undo_stage_hunk<CR>', { noremap = true, desc = 'Undo stage hunk' })
map('n', '<leader>hp', ':Gitsigns preview_hunk<CR>', { noremap = true, desc = 'Preview hunk' })
map('n', '<leader>hb', ':Gitsigns blame_line<CR>', { noremap = true, desc = 'Blame line' })
map('n', '<leader>hr', ':Gitsigns reset_hunk<CR>', { noremap = true, desc = 'Reset hunk' })
map('n', '<leader>hR', ':Gitsigns reset_buffer<CR>', { noremap = true, desc = 'Reset buffer' })
map({ 'o', 'x' }, 'ih', ':<C-U>Gitsigns select_hunk<CR>', { noremap = true, desc = 'Select hunk' }) --text object
