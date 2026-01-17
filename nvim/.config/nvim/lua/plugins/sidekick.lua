return {
    {
        "folke/sidekick.nvim",
        opts = {
            -- add any options here
            nes = { enabled = false },
            copilot = {
                status = { enabled = false },
            },
        },
        cmd = "Sidekick",
        keys = {
            {
                "<leader>at",
                function()
                    require("sidekick.cli").send({ msg = "{this}" })
                end,
                mode = { "x", "n" },
                desc = "Send This",
            },
            {
                "<leader>af",
                function()
                    require("sidekick.cli").send({ msg = "{file}" })
                end,
                desc = "Send File",
            },
            {
                "<leader>av",
                function()
                    require("sidekick.cli").send({ msg = "{selection}" })
                end,
                mode = { "x" },
                desc = "Send Visual Selection",
            },
            -- Example of a keybinding to open Claude directly
            {
                "<leader>la",
                function()
                    require("sidekick.cli").toggle({ name = "claude", focus = true })
                end,
                desc = "Sidekick Toggle Claude",
            },
        },
    },
}
