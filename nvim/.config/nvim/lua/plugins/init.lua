return {
  -- Helps with intendation settings using editorconfig standard
  { "tpope/vim-sleuth" },
  -- Enables support to manipulate surrounding text objects like cs'" will make 'text' -> "text"
  { "tpope/vim-surround" },
  -- Enables the default last command with period behaviour for custom mappings
  { "tpope/vim-repeat" },
  -- Pairs of handy bracket mappings like [b or ]b
  { "tpope/vim-unimpaired" },
  -- Navigate between tmux pane and vim splits seamlessly <C-h,j,k,l>
  { "christoomey/vim-tmux-navigator" },
  -- Enables * search for visually selected texts
  { "nelstrom/vim-visual-star-search" },
  -- Schemas for JSON, YAML etc.
  { "b0o/schemastore.nvim",           lazy = true },
  -- More text objects for HTML and XML attributes so we can do `vix` to select an html attribute same goes for c,y & d operations
  {
    'whatyouhide/vim-textobj-xmlattr',
    dependencies = { 'kana/vim-textobj-user' }
  },
  -- Notifier from snacks.nvim
  {
    "folke/snacks.nvim",
    priority = 1000,
    ---@type snacks.Config
    opts = {
      notifier = {
        -- your notifier configuration comes here
        -- or leave it empty to use the default settings
        -- refer to the configuration section below
      }
    }
  },

  -- For distraction free writing
  { "folke/twilight.nvim", opts = {} },
  {
    "folke/zen-mode.nvim",
    opts = {
      window = {
        width = 0.9,
      }
    },
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

  -- Can split & join arrays and methods into new lines or single line
  {
    "AndrewRadev/splitjoin.vim",
    config = function()
      vim.g.splitjoin_html_attributes_bracket_on_new_line = 1
      vim.g.splitjoin_trailing_comma = 1
      vim.g.splitjoin_php_method_chain = 1
    end,
  },

  -- Blade file highlighting
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
    "hat0uma/csvview.nvim",
    ---@module "csvview"
    ---@type CsvView.Options
    opts = {
      parser = { comments = { "#", "//" } },
      keymaps = {
        -- Text objects for selecting fields
        textobject_field_inner = { "if", mode = { "o", "x" } },
        textobject_field_outer = { "af", mode = { "o", "x" } },
        -- Excel-like navigation:
        -- Use <Tab> and <S-Tab> to move horizontally between fields.
        -- Use <Enter> and <S-Enter> to move vertically between rows and place the cursor at the end of the field.
        -- Note: In terminals, you may need to enable CSI-u mode to use <S-Tab> and <S-Enter>.
        jump_next_field_end = { "<Tab>", mode = { "n", "v" } },
        jump_prev_field_end = { "<S-Tab>", mode = { "n", "v" } },
        jump_next_row = { "<Enter>", mode = { "n", "v" } },
        jump_prev_row = { "<S-Enter>", mode = { "n", "v" } },
      },
    },
    cmd = { "CsvViewEnable", "CsvViewDisable", "CsvViewToggle" },
  }
}
