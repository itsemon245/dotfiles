-- LSP Logic on_attach
local lspLogics = function(client, event)
  if client then
    client.server_capabilities.hoverProvider = true
  end
  -- Diagnostic configuration
  vim.diagnostic.config({
    virtual_text = false,
    float = {
      source = true,
    },
  })
  -- Sign configuration
  vim.fn.sign_define("DiagnosticSignError", { text = "", texthl = "DiagnosticSignError" })
  vim.fn.sign_define("DiagnosticSignWarn", { text = "", texthl = "DiagnosticSignWarn" })
  vim.fn.sign_define("DiagnosticSignInfo", { text = "", texthl = "DiagnosticSignInfo" })
  vim.fn.sign_define("DiagnosticSignHint", { text = "", texthl = "DiagnosticSignHint" })

  -- Utilty function for keymap
  local map = function(keys, func, desc)
    vim.keymap.set("n", keys, func, { desc = "LSP: " .. desc })
  end

  map("gd", require("telescope.builtin").lsp_definitions, "[G]oto [D]efinition")
  map("gD", vim.lsp.buf.declaration, "[G]oto [D]eclaration")
  map("gr", require("telescope.builtin").lsp_references, "[G]oto [R]eferences")
  map("gI", require("telescope.builtin").lsp_implementations, "[G]oto [I]mplementation")
  map("<Leader>d", "<cmd>lua vim.diagnostic.open_float()<CR>", "[D]iagnostics Popover")
  map("<leader>D", require("telescope.builtin").lsp_type_definitions, "Type [D]efinition")
  -- Go back and forth in code diagnostics
  map("[d", "<cmd>lua vim.diagnostic.goto_prev()<CR>", "Previous Diagnostics")
  map("]d", "<cmd>lua vim.diagnostic.goto_next()<CR>", "Next Diagnostics")
  --  Symbols are things like variables, functions, types, etc.
  map("<leader>ds", require("telescope.builtin").lsp_document_symbols, "[D]ocument [S]ymbols")
  map("<leader>ws", require("telescope.builtin").lsp_dynamic_workspace_symbols, "[W]orkspace [S]ymbols")
  map("<leader>rn", vim.lsp.buf.rename, "[R]e[n]ame Variable")
  map("<leader>ca", vim.lsp.buf.code_action, "[C]ode [A]ction")
  map("K", vim.lsp.buf.hover, "Hover Documentation")

  -- The following two autocommands are used to highlight references of the
  -- word under your cursor when your cursor rests there for a little while.
  --    See `:help CursorHold` for information about when this is executed
  --
  -- When you move your cursor, the highlights will be cleared (the second autocommand).
  if client and client.supports_method(vim.lsp.protocol.Methods.textDocument_documentHighlight) then
    local highlight_augroup = vim.api.nvim_create_augroup('kickstart-lsp-highlight', { clear = false })
    vim.api.nvim_create_autocmd({ 'CursorHold', 'CursorHoldI' }, {
      buffer = event.buf,
      group = highlight_augroup,
      callback = vim.lsp.buf.document_highlight,
    })

    vim.api.nvim_create_autocmd({ 'CursorMoved', 'CursorMovedI' }, {
      buffer = event.buf,
      group = highlight_augroup,
      callback = vim.lsp.buf.clear_references,
    })

    vim.api.nvim_create_autocmd('LspDetach', {
      group = vim.api.nvim_create_augroup('kickstart-lsp-detach', { clear = true }),
      callback = function(event2)
        vim.lsp.buf.clear_references()
        vim.api.nvim_clear_autocmds { group = 'kickstart-lsp-highlight', buffer = event2.buf }
      end,
    })
  end
  -- The following code creates a keymap to toggle inlay hints in your
  -- code, if the language server you are using supports them
  --
  -- This may be unwanted, since they displace some of your code
  if client and client.supports_method(vim.lsp.protocol.Methods.textDocument_inlayHint) then
    map('<leader>th', function()
      vim.lsp.inlay_hint.enable(not vim.lsp.inlay_hint.is_enabled { bufnr = event.buf })
    end, '[T]oggle Inlay [H]ints')
  end
end
local on_attach = function(event)
  local client = vim.lsp.get_client_by_id(event.data.client_id)
  -- Retry after 1 second if client is not found
  if not client then
    vim.defer_fn(function()
      local client_retry = vim.lsp.get_client_by_id(event.data.client_id)
      if client_retry then
        lspLogics(client_retry, event)
      end
    end, 1000)         -- Retry after 1 second
    return
  end
  lspLogics(client, event)
end
return on_attach
