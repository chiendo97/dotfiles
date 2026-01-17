return {
    {
        "lukas-reineke/indent-blankline.nvim",
        enabled = false,
        event = "VeryLazy",
        main = "ibl",
        config = function()
            require("ibl").setup({
                indent = { char = "|" },
                exclude = {
                    filetypes = {
                        "org",
                        "go",
                        "help",
                        "terminal",
                        "dashboard",
                        "packer",
                        "lspinfo",
                        "TelescopePrompt",
                        "TelescopeResults",
                        "NvimTree",
                    },
                    buftypes = {
                        "terminal",
                        "qf",
                        "quickfix",
                        "terminal",
                        "packer",
                    },
                },
                scope = {
                    enabled = true,
                    highlight = { "Function", "Label" },
                    priority = 500,
                    show_start = false,
                    show_end = false,
                    include = {
                        node_type = {
                            python = {
                                "if_statement",
                                "for_statement",
                                "with_statement",
                                "while_statement",
                                "table_constructor",
                            },
                            go = {
                                "if_statement",
                                "for_statement",
                                "while_statement",
                                "table_constructor",
                            },
                            zig = {
                                "if_statement",
                                "for_statement",
                                "while_statement",
                                "table_constructor",
                            },
                            lua = {
                                "if_statement",
                                "for_statement",
                                "while_statement",
                                "table_constructor",
                            },
                        },
                    },
                },
            })
        end,
    },
}
