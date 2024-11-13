-- This will override `vim.lsp.protocol.CompletionItemKind` icons
-- with the ones provided in this table
-- Override default icons

local icons = {
  Text = " ",         -- Text icon
  Method = " ",       -- Method icon
  Function = " ",     -- Function icon
  Constructor = " ",  -- Constructor icon
  Field = " ",        -- Field icon
  Variable = " ",     -- Variable icon
  Class = " ",        -- Class icon
  Interface = " ",    -- Interface icon
  Module = " ",       -- Module icon
  Property = " ",     -- Property icon
  Unit = " ",         -- Unit icon
  Value = " ",        -- Value icon
  Enum = " ",         -- Enum icon
  Keyword = " ",      -- Keyword icon
  Snippet = " ",      -- Snippet icon
  Color = " ",        -- Color icon
  File = " ",         -- File icon
  Reference = " ",    -- Reference icon
  Folder = " ",       -- Folder icon
  EnumMember = " ",   -- Enum member icon
  Constant = " ",     -- Constant icon
  Struct = " ",       -- Struct icon
  Event = " ",        -- Event icon
  Operator = " ",     -- Operator icon
  TypeParameter = " ",-- Type parameter icon
}
vim.lsp.protocol.CompletionItemKind = icons
return {}
