return {
    {
        "stevearc/oil.nvim",
        cmd = "Oil",
        enabled = false,
        opts = {},
    },
    {
        "A7Lavinraj/fyler.nvim",
        enabled = false,
        branch = "stable", -- Use stable branch for production
        lazy = false, -- Necessary for `default_explorer` to work properly
        opts = {
            views = {
                finder = {
                    close_on_select = false,
                    confirm_simple = true,
                    git_status = { enabled = false },
                    mappings = {
                        ["<C-v>"] = "SelectVSplit",
                        ["<C-s>"] = "SelectSplit",
                    },
                    mappings_opts = {
                        desc = "Fyler",
                    },
                    win = { win_opts = { cursorline = true } },
                },
            },
        },
        keys = {
            {
                "<leader>c",
                function()
                    require("fyler").toggle({
                        kind = "split_left_most",
                    })
                end,
                desc = "Open Fyler",
                mode = { "n" },
            },
        },
    },
}
