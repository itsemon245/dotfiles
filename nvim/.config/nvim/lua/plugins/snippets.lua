return {
  "L3MON4D3/LuaSnip",
  tag = "v2.*",
  run = "make install_jsregexp",
  dependencies = {
    "saadparwaiz1/cmp_luasnip",
    "rafamadriz/friendly-snippets",
    "onecentlin/laravel-blade-snippets-vscode",
  },
  config = function()
    local luasnip = require("luasnip")
    local types = require("luasnip.util.types")
    local suggestion = require('supermaven-nvim.completion_preview')

    luasnip.config.set_config({
      keep_roots = true,
      link_roots = true,
      link_children = true,
      history = true,
      delete_check_events = "TextChanged",
      updateevents = "TextChanged,TextChangedI",
      ext_opts = {
        [types.choiceNode] = {
          active = {
            virt_text = { { "choiceNode", "Comment" } },
          },
        },
      },
    })

    -- Bindings for expanding snippets
    vim.keymap.set({ "i", "s" }, "<C-l>", function()
      if luasnip.expand_or_jumpable() then
        luasnip.expand_or_jump()
      elseif suggestion.has_suggestion() then
        suggestion.on_accept_suggestion()
      end
    end, { silent = true })
    vim.keymap.set({ "i", "s" }, "<C-h>", function()
      if luasnip.jumpable(-1) then
        luasnip.jump(-1)
      end
    end, { silent = true })
    vim.keymap.set({ "i", "s" }, "<C-k>", function()
      if luasnip.choice_active() then
        luasnip.change_choice(1)
      end
    end, { silent = true })
    -- Extending filetypes for snippets in embedded languages
    luasnip.filetype_extend("html", { "javascript" })
    luasnip.filetype_extend("php", { "html" })
    luasnip.filetype_extend("php", { "phpdoc" })
    luasnip.filetype_extend("php", { "blade" })
    luasnip.filetype_extend('javascriptreact', { 'javascript' })
    luasnip.filetype_extend('typescriptreact', { 'typescript' })
    luasnip.filetype_extend("vue", { "html" })

    -- load vscode style snippets -- Uses the friendly-snippets repo
    require("luasnip.loaders.from_vscode").lazy_load()
    -- load snipmate style snippets -- Uses the snippets folder for custom snippets
    require("luasnip.loaders.from_snipmate").lazy_load({ paths = { "~/.config/nvim/snippets" } })

    -- Some shortands and helpers
    local ls = luasnip
    local s = ls.snippet
    local sn = ls.snippet_node
    local t = ls.text_node
    local i = ls.insert_node
    local f = ls.function_node
    local c = ls.choice_node
    local d = ls.dynamic_node
    local r = ls.restore_node
    local l = require("luasnip.extras").lambda
    local rep = require("luasnip.extras").rep
    local p = require("luasnip.extras").partial
    local m = require("luasnip.extras").match
    local n = require("luasnip.extras").nonempty
    local dl = require("luasnip.extras").dynamic_lambda
    local fmt = require("luasnip.extras.fmt").fmt
    local fmta = require("luasnip.extras.fmt").fmta
    local conds = require("luasnip.extras.conditions")
    local conds_expand = require("luasnip.extras.conditions.expand")

    -- args is a table, where 1 is the text in Placeholder 1, 2 the text in
    -- placeholder 2,...
    local function copy(args)
      return args[1]
    end

    -- 'recursive' dynamic snippet. Expands to some text followed by itself.
    local rec_ls
    rec_ls = function()
      return sn(
        nil,
        c(1, {
          -- Order is important, sn(...) first would cause infinite loop of expansion.
          t(""),
          sn(nil, { t({ "", "\t\\item " }), i(1), d(2, rec_ls, {}) }),
        })
      )
    end

    -- complicated function for dynamicNode.
    local function jdocsnip(args, _, old_state)
    end

    -- Make sure to not pass an invalid command, as io.popen() may write over nvim-text.
    local function bash(_, _, command)
    end

    -- Returns a snippet_node wrapped around an insertNode whose initial
    -- text value is set to the current date in the desired format.
    local date_input = function(args, snip, old_state, fmt)
      local fmt = fmt or "%Y-%m-%d"
      return sn(nil, i(1, os.date(fmt)))
    end

    -- Define luasnip snippets here
    -- @see https://github.com/L3MON4D3/LuaSnip/blob/master/Examples/snippets.lua
    ls.add_snippets("php", {
      s(
        "fmt3",
        fmt("{} {a} {} {1} {}", {
          t("changing 1"),
          t("changing 2"),
          a = t("A"),
        })
      ),
      s(
        "pubf",
        fmt([[
    /**
     * Undocumented function
    {}
     * @return {}
     */
    {}function {}({}):{} {{
        {}
    }}
    ]], {
          f(function(args)
            local params = vim.split(args[1][1] or "", ",", true)
            local params_desc = {}
            for i, param in ipairs(params) do
              param = vim.trim(param)
              if #param > 0 then
                table.insert(params_desc, " * @param " .. param)
              end
            end
            return params_desc
          end, { 3 }),                                                   -- params_desc
          rep(4),                                                        -- return_type
          c(1, { t(""), t("public "), t("private "), t("protected ") }), -- visibility
          i(2, 'name'),                                                  -- function name
          i(3),                                                          -- parameters
          i(4),                                                          -- return type
          i(5)
        }, { strict = false })
      ),
    })
  end
}
