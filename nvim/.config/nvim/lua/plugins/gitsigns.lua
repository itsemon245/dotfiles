return {
  'lewis6991/gitsigns.nvim',
  config = function()
    require('gitsigns').setup({current_line_blame = true})
    vim.opt.signcolumn = 'yes:1';
    vim.keymap.set('n', ']h', ':Gitsigns next_hunk<CR>')
    vim.keymap.set('n', '[h', ':Gitsigns prev_hunk<CR>')
    vim.keymap.set('n', 'gs', ':Gitsigns stage_hunk<CR>')
    vim.keymap.set('n', 'gS', ':Gitsigns undo_stage_hunk<CR>')
    vim.keymap.set('n', 'gp', ':Gitsigns preview_hunk<CR>')
    vim.keymap.set('n', 'gb', ':Gitsigns blame_line<CR>', {remap = true})

  end,
}
