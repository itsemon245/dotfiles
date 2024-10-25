return {
  "nvim-neo-tree/neo-tree.nvim",
  branch = "v3.x",
  dependencies = {
    "nvim-lua/plenary.nvim",
    "nvim-tree/nvim-web-devicons", -- not strictly required, but recommended
    "MunifTanjim/nui.nvim",
    "3rd/image.nvim",            -- Optional image support in preview window: See `# Preview Mode` for more information
  },
  keys = {
    { "<C-n>", "<cmd>Neotree toggle position=right<cr>",  desc = "Focus Neotree" },
  },
  opts = {
    window = {
      width = 30,
    },
    filesystem = {
      follow_current_file = {
        enabled = true,
          leave_dirs_open = false,
        },
      filtered_items = {
        hide_dotfiles = false,
      }
    },
  },
}
