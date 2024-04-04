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
    { "<C-b>", "<cmd>Neotree toggle<cr>", desc = "Toggle NeoTree" },
    { "<C-n>", "<cmd>Neotree focus<cr>",  desc = "Focus Neotree" },
  },
  opts = {
    window = {
      width = 30,
    },
    filesystem = {
      filtered_items = {
        hide_dotfiles = false,
        alaways_show = {
          ".env",
        }
      }
    }
  },
  --  config = function()
  --  vim.keymap.set('n', '<C-n>', ":Neotree reveal<cr>", {})
  --end
}
