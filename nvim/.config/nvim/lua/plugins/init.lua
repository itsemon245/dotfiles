return {
  -- Helps with intendation settings using editorconfig standard
  { "tpope/vim-sleuth" },
  -- Enables support to manipulate surrounding text objects like cs'" will make 'text' -> "text"
  { "tpope/vim-surround" },
  -- Gives some UNIX commands as helper functions for vi, such as :Rename :SudoWrite :Chmod etc
  { "tpope/vim-eunuch" },
  -- Enables the default last command with period behaviour for custom mappings
  { "tpope/vim-repeat" },
  -- Pairs of handy bracket mappings like [b or ]b
  { "tpope/vim-unimpaired" },
  -- Remembers the last cursor position of the file
  { "farmergreg/vim-lastplace" },
  -- Navigate between tmux pane and vim splits seamlessly <C-h,j,k,l>
  { "christoomey/vim-tmux-navigator" },
  -- Enables * search for visually selected texts
  { "nelstrom/vim-visual-star-search" },
  -- Creates parent directories for a file if not exists
  { "jessarcher/vim-heritage" },
  -- More text objects for HTML and XML attributes so we can do `vix` to select an html attribute same goes fo c,y & d
  {
    'whatyouhide/vim-textobj-xmlattr',
    dependencies = { 'kana/vim-textobj-user' }
  },
  -- Notifier from snacks.nvim
  {
    "folke/snacks.nvim",
    ---@type snacks.Config
    opts = {
      notifier = {
        -- your notifier configuration comes here
        -- or leave it empty to use the default settings
        -- refer to the configuration section below
      }
    }
  },

  -- Adds closing brackets, quotes etc.
  {
    "windwp/nvim-autopairs",
    config = function()
      require("nvim-autopairs").setup()
    end,
  },

  -- Add smooth scrolling for jumps
  {
    "karb94/neoscroll.nvim",
    config = function()
      require("neoscroll").setup()
    end,
  },
  {
    "famiu/bufdelete.nvim",
    config = function()
      vim.keymap.set('n', '<Leader>q', ':Bdelete<CR>')
    end,
  },

  {
    "sickill/vim-pasta",
    config = function()
      vim.g.pasta_disable_filetypes = { 'fugitive' }
    end,
  },

  -- Can split & join arrays and methods into new lines or single line. TODO: it's asking for github username and password
  -- {
  -- "AndrewRadev/splitjoin.nvim",
  -- config = function()
  -- vim.g.splitjoin_html_attributes_bracket_on_new_line = 1
  -- vim.g.splitjoin_trailing_comma = 1
  -- vim.g.splitjoin_php_method_chain = 1
  -- end,
  -- },

  -- { "sheerun/vim-polyglot" }, --TODO: Needs Fixing

  -- Catppuccin color scheme
  {
    'jwalton512/vim-blade',
    opts = {},
    config = function()
      vim.g.blade_extended_highlighting = 1
    end,
  },
  {
    -- Add the blade-nav.nvim plugin which provides Goto File capabilities
    -- for Blade files.
    "ricardoramirezr/blade-nav.nvim",
    dependencies = {
      "hrsh7th/nvim-cmp",
    },
    ft = { "blade", "php" },
    opts = {
      close_tag_on_complete = false, -- default: true
    }
  },
  -- Displays indent line
  {
    'lukas-reineke/indent-blankline.nvim',
    main = "ibl",
    ---@module "ibl"
    ---@type ibl.config
    opts = {
    },
  },

  {
    "nathom/filetype.nvim",
    opts = {
      overrides = {
        complex = {
          ["*.blade.php"] = "blade",
        },
      }
    }
  },
  {
    "mskelton/termicons.nvim",
    dependecies = { "nvim-tree/nvim-web-devicons" },
    build = false,
    opts = {},
  }
}
