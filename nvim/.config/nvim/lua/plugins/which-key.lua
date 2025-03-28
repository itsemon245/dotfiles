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

    -- Document existing key chains
    require('which-key').register {
      ['<leader>c'] = { name = '[C]ode', _ = 'which_key_ignore' },
      ['<leader>d'] = { name = '[D]ocument', _ = 'which_key_ignore' },
      ['<leader>r'] = { name = '[R]ename', _ = 'which_key_ignore' },
      ['<leader>s'] = { name = '[S]earch', _ = 'which_key_ignore' },
      ['<leader>w'] = { name = '[W]orkspace', _ = 'which_key_ignore' },
    }
  end,
}
