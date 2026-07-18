return {
  -- Markdown renderer
  {
    'MeanderingProgrammer/render-markdown.nvim',
    dependencies = { 'nvim-treesitter/nvim-treesitter' },
    -- dependencies = { 'nvim-treesitter/nvim-treesitter', 'nvim-mini/mini.icons' },        -- if you use standalone mini plugins
    -- dependencies = { 'nvim-treesitter/nvim-treesitter', 'nvim-tree/nvim-web-devicons' }, -- if you prefer nvim-web-devicons
    ---@module 'render-markdown'
    ---@type render.md.UserConfig
    opts = {
      code = {
        language_name = false,
      }

    },
  },

  -- Markdown Helper
  -- {
  --   'jakewvincent/mkdnflow.nvim',
  --   ft = { 'markdown', 'rmd' }, -- Add custom filetypes here if configured
  --   config = function()
  --     require('mkdnflow').setup({
  --       mappings = {
  --         MkdnEnter = { { 'n', 'v' }, '<CR>' },
  --         MkdnGoBack = { 'n', '<BS>' },
  --         MkdnGoForward = { 'n', '<Del>' },
  --         MkdnMoveSource = { 'n', '<F2>' },
  --         MkdnNextLink = { 'n', '<Tab>' },
  --         MkdnPrevLink = { 'n', '<S-Tab>' },
  --         MkdnFollowLink = false,
  --         MkdnDestroyLink = { 'n', '<M-CR>' },
  --         MkdnTagSpan = { 'v', '<M-CR>' },
  --         MkdnYankAnchorLink = { 'n', 'yaa' },
  --         MkdnYankFileAnchorLink = { 'n', 'yfa' },
  --         MkdnNextHeading = { 'n', ']]' },
  --         MkdnPrevHeading = { 'n', '[[' },
  --         MkdnNextHeadingSame = { 'n', '][' },
  --         MkdnPrevHeadingSame = { 'n', '[]' },
  --         MkdnIncreaseHeading = { { 'n', 'v' }, '+' },
  --         MkdnDecreaseHeading = { { 'n', 'v' }, '-' },
  --         MkdnIncreaseHeadingOp = { { 'n', 'v' }, 'g+' },
  --         MkdnDecreaseHeadingOp = { { 'n', 'v' }, 'g-' },
  --         MkdnToggleToDo = { { 'n', 'v' }, '<C-Space>' },
  --         MkdnNewListItem = true,
  --         MkdnNewListItemBelowInsert = { 'n', 'o' },
  --         MkdnNewListItemAboveInsert = { 'n', 'O' },
  --         MkdnExtendList = false,
  --         MkdnUpdateNumbering = { 'n', '<leader>nn' },
  --         MkdnTableNextCell = { 'i', '<Tab>' },
  --         MkdnTablePrevCell = { 'i', '<S-Tab>' },
  --         MkdnTableNextRow = false,
  --         MkdnTablePrevRow = { 'i', '<M-CR>' },
  --         MkdnTableNewRowBelow = { 'n', '<leader>ir' },
  --         MkdnTableNewRowAbove = { 'n', '<leader>iR' },
  --         MkdnTableNewColAfter = { 'n', '<leader>ic' },
  --         MkdnTableNewColBefore = { 'n', '<leader>iC' },
  --         MkdnTableDeleteRow = { 'n', '<leader>dr' },
  --         MkdnTableDeleteCol = { 'n', '<leader>dc' },
  --         MkdnTableAlignLeft = { 'n', '<leader>al' },
  --         MkdnTableAlignRight = { 'n', '<leader>ar' },
  --         MkdnTableAlignCenter = { 'n', '<leader>ac' },
  --         MkdnTableAlignDefault = { 'n', '<leader>ax' },
  --         MkdnFoldSection = { 'n', '<leader>f' },
  --         MkdnUnfoldSection = { 'n', '<leader>F' },
  --         MkdnTab = false,
  --         MkdnSTab = false,
  --         MkdnIndentListItem = { 'i', '<C-t>' },
  --         MkdnDedentListItem = { 'i', '<C-d>' },
  --         MkdnCreateLink = false,
  --         MkdnCreateLinkFromClipboard = { { 'n', 'v' }, '<leader>p' },
  --       },
  --     })
  --   end
  -- }


}
