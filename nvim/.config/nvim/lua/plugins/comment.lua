return {
    'numToStr/Comment.nvim',
    opts = {
        -- add any options here
    },
    lazy = false, 
    keys = {
      { "<C-c>", "gcc", desc = "Comment Line", remap = true },
      { "<C-c>", "gc", desc = "Comment Block", remap = true, mode = "v" },
      { "<leader>/", "gcc", desc = "[Toggle] Comment Line", remap = true },
      { "<leader>/", "gc", desc = "Comment Block", remap = true, mode = "v" },
    },
}
