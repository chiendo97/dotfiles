return {
    {
        "chiendo97/chatml.nvim",
        dev = true,
        branch = "cle/mcp",
        opts = {},
        keys = {
            {
                "<leader>lc",
                function()
                    require("chatml/chat").new_chat()
                end,
                mode = { "n" },
                desc = "Create new chatml chat",
            },
            {
                "<leader>lp",
                function()
                    require("chatml/chat").picker()
                end,
                mode = { "n" },
                desc = "Picker chatml chat",
            },
            {
                "<leader>lg",
                function()
                    require("chatml/chat").search()
                end,
                mode = { "n" },
                desc = "Picker chatml chat",
            },
        },
        dependencies = {
            "ravitemer/mcphub.nvim",
            "j-hui/fidget.nvim",
        },
    },
}
