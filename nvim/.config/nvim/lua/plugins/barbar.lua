return {
  'romgrk/barbar.nvim',
  dependencies = {
    'lewis6991/gitsigns.nvim', -- OPTIONAL: for git status
    'nvim-tree/nvim-web-devicons', -- OPTIONAL: for file icons
  },
  config = function()
    vim.g.barbar_auto_setup = false 
	end,
  opts = {
    -- lazy.nvim will automatically call setup for you. put your options here, anything missing will use the default:
    animation = true,
    no_name_title = nil,
    -- sorting options
    sort = {
      -- tells barbar to ignore case differences while sorting buffers
      ignore_case = true,
    },
  }
}
