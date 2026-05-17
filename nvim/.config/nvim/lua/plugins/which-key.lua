-- Useful plugin to show you pending keybinds.
return {
  'folke/which-key.nvim',
  dependencies = {
    "echasnovski/mini.icons"
  },
  event = 'VimEnter',
  config = function()
    require('which-key').setup({
        preset = 'classic',
        notify = false,
    })

    require('which-key').add({
      { '<leader>c', group = '[C]ode' },
      { '<leader>d', group = '[D]ocument' },
      { '<leader>r', group = '[R]ename' },
      { '<leader>s', group = '[S]earch' },
      { '<leader>w', group = '[W]orkspace' },
    })
  end,
}
