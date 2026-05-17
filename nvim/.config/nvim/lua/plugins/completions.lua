return {
  {
    "L3MON4D3/LuaSnip",
    version = "v2.*",
    build = "make install_jsregexp",
    dependencies = {
      "rafamadriz/friendly-snippets",
      "onecentlin/laravel-blade-snippets-vscode",
    },
    config = function()
      local luasnip = require("luasnip")
      local types = require("luasnip.util.types")
      local fmt = require("luasnip.extras.fmt").fmt
      local rep = require("luasnip.extras").rep
      local s = luasnip.snippet
      local t = luasnip.text_node
      local i = luasnip.insert_node
      local f = luasnip.function_node
      local c = luasnip.choice_node

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

      vim.keymap.set({ "i", "s" }, "<C-l>", function()
        local ok, suggestion = pcall(require, "supermaven-nvim.completion_preview")
        if luasnip.expand_or_jumpable() then
          luasnip.expand_or_jump()
        elseif ok and suggestion.has_suggestion() then
          suggestion.on_accept_suggestion()
        end
      end, { silent = true, desc = "Expand snippet or accept suggestion" })

      vim.keymap.set({ "i", "s" }, "<C-h>", function()
        if luasnip.jumpable(-1) then
          luasnip.jump(-1)
        end
      end, { silent = true, desc = "Previous snippet field" })

      vim.keymap.set({ "i", "s" }, "<C-k>", function()
        if luasnip.choice_active() then
          luasnip.change_choice(1)
        end
      end, { silent = true, desc = "Next snippet choice" })

      luasnip.filetype_extend("html", { "javascript" })
      luasnip.filetype_extend("php", { "html", "phpdoc", "blade" })
      luasnip.filetype_extend("javascriptreact", { "javascript" })
      luasnip.filetype_extend("typescriptreact", { "typescript" })
      luasnip.filetype_extend("vue", { "html" })

      require("luasnip.loaders.from_vscode").lazy_load()
      require("luasnip.loaders.from_snipmate").lazy_load({ paths = { "~/.config/nvim/snippets" } })

      luasnip.add_snippets("php", {
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
              for _, param in ipairs(params) do
                param = vim.trim(param)
                if #param > 0 then
                  table.insert(params_desc, " * @param " .. param)
                end
              end
              return params_desc
            end, { 3 }),
            rep(4),
            c(1, { t(""), t("public "), t("private "), t("protected ") }),
            i(2, "name"),
            i(3),
            i(4),
            i(5),
          }, { strict = false })
        ),
      })
    end,
  },

  {
    "saghen/blink.cmp",
    version = "*",
    dependencies = {
      "L3MON4D3/LuaSnip",
      "rafamadriz/friendly-snippets",
    },
    ---@module 'blink.cmp'
    ---@type blink.cmp.Config
    opts = {
      keymap = { preset = "enter" },
      appearance = {
        nerd_font_variant = "mono",
      },
      completion = {
        documentation = { auto_show = true },
        list = {
          selection = {
            preselect = false,
            auto_insert = true,
          }
        },
        menu = {
          auto_show = true,
          draw = {
            columns = {
              { "label", "kind_icon", gap = 4 },
              { "kind", gap = 1 },
            },
          }
        }
      },
      sources = {
        default = { "lsp", "path", "snippets", "buffer" },
      },
      fuzzy = { implementation = "prefer_rust_with_warning" },
    },
    opts_extend = { "sources.default" },
  }
}
