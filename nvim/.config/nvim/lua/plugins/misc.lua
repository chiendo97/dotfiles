return {
    {
        "juniorsundar/cling.nvim",
        cmd = { "Cling" },
        config = function()
            require("cling").setup({
                wrappers = {
                    {
                        binary = "docker",
                        command = "Docker",
                        help_cmd = "--help",
                    },
                    {
                        binary = "eza",
                        command = "Eza",
                        completion_file = "https://raw.githubusercontent.com/eza-community/eza/main/completions/bash/eza",
                    },
                },
            })
        end,
    },
    {
        "carlos-algms/agentic.nvim",
        event = "VeryLazy",
        opts = {
            -- Available by default: "claude-acp" | "gemini-acp" | "codex-acp" | "opencode-acp" | "cursor-acp"
            provider = "claude-acp", -- setting the name here is all you need to get started
            acp_providers = {
                ["claude-acp"] = {
                    -- Automatically switch to this mode when a new session starts
                    default_mode = "bypassPermissions",
                },
            },
        },
        -- these are just suggested keymaps; customize as desired
        keys = {
            {
                "<C-\\>",
                function()
                    require("agentic").toggle()
                end,
                mode = { "n", "v", "i" },
                desc = "Toggle Agentic Chat",
            },
            {
                "<C-'>",
                function()
                    require("agentic").add_selection_or_file_to_context()
                end,
                mode = { "n", "v" },
                desc = "Add file or selection to Agentic to Context",
            },
            {
                "<C-,>",
                function()
                    require("agentic").new_session()
                end,
                mode = { "n", "v", "i" },
                desc = "New Agentic Session",
            },
        },
    },
    {
        "necrom4/calcium.nvim",
        cmd = { "Calcium" },
        opts = {},
    },
    {
        "brianhuster/live-preview.nvim",
        config = function()
            require("livepreview.config").set({
                port = 5500,
                browser = "",
                dynamic_root = false,
                sync_scroll = true,
                picker = "vim.ui.select",
                address = "127.0.0.1",
            })
        end,
        command = { "LivePreview" },
    },
}
