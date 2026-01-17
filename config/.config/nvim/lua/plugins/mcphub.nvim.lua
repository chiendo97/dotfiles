local is_mcphub_available = vim.fn.executable("mcp-hub") == 1

return {
    {
        "ravitemer/mcphub.nvim",
        enabled = is_mcphub_available,
        opts = {
            auto_approve = true, -- Auto approve mcp tool calls
        },
        dependencies = {
            "nvim-lua/plenary.nvim",
        },
    },
}
