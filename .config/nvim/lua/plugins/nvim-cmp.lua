local cmp = require("cmp")

local feedkey = function(key, mode)
    vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes(key, true, true, true), mode, true)
end

cmp.setup({
    snippet = {
        expand = function(args)
            vim.fn["vsnip#anonymous"](args.body)
        end,
    },

    window = {
        -- completion = cmp.config.window.bordered(),
        -- documentation = cmp.config.window.bordered(),
    },

    preselect = require("cmp.types").cmp.PreselectMode.None,

    -- You must set mapping if you want.
    mapping = {
        ["<C-Space>"] = cmp.mapping(cmp.mapping.complete(), { "i", "c" }),
        ["<C-e>"] = cmp.mapping({ i = cmp.mapping.abort(), c = cmp.mapping.close() }),

        ["<CR>"] = cmp.mapping.confirm({ select = true }), -- Accept currently selected item. Set `select` to `false` to only confirm explicitly selected items.
        ["<C-p>"] = cmp.mapping.select_prev_item(),
        ["<C-n>"] = cmp.mapping.select_next_item(),

        ["<Tab>"] = cmp.mapping(function(fallback)
            if vim.fn["vsnip#jumpable"]() == 1 then
                feedkey("<Plug>(vsnip-jump-next)", "")
            else
                fallback()
            end
        end, {
            "i",
            "s",
        }),
        ["<S-Tab>"] = cmp.mapping(function(fallback)
            if vim.fn["vsnip#jumpable"](-1) == 1 then
                feedkey("<Plug>(vsnip-jump-prev)", "")
            else
                fallback()
            end
        end, {
            "i",
            "s",
        }),
    },

    -- You should specify your *installed* sources.
    sources = {
        { name = "nvim_lsp" },
        { name = "vsnip" },
        { name = "buffer" },
    },

    formatting = {
        format = function(entry, vim_item)
            -- set a name for each source
            vim_item.menu = ({
                path = "[Path]",
                buffer = "[Buffer]",
                nvim_lsp = "[LSP]",
                luasnip = "[LuaSnip]",
                vsnip = "[VSnip]",
                nvim_lua = "[Lua]",
                latex_symbols = "[Latex]",
                orgmode = "[OrgMode]",
                neorg = "[NeOrg]",
            })[entry.source.name]
            return vim_item
        end,
    },

    experimental = {
        native_menu = false,
        ghost_text = true,
    },

    sorting = {
        comparators = {
            cmp.config.compare.offset,
            cmp.config.compare.exact,
            cmp.config.compare.score,
            cmp.config.compare.length,
            cmp.config.compare.kind,
            cmp.config.compare.sort_text,
            cmp.config.compare.order,
        },
    },
})
