return {
    {
        "folke/which-key.nvim",
        enabled = true,
        event = "VeryLazy",
        opts = {
            preset = "helix",
            delay = 300,
            triggers = {
                { "<auto>", mode = "nixsotc" },
            },
        },
        keys = {
            {
                "<leader>?",
                function()
                    require("which-key").show({ global = false })
                end,
                desc = "Buffer Local Keymaps (which-key)",
            },
        },
    },
}
