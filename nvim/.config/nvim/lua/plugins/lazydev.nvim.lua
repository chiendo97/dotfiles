return {
    {
        "folke/lazydev.nvim",
        ft = "lua", -- only load on lua files
        opts = {
            library = {
                -- Or relative, which means they will be resolved from the plugin dir.
                "lazy.nvim",
                -- It can also be a table with trigger words / mods
                -- Only load luvit types when the `vim.uv` word is found
                { path = "${3rd}/luv/library", words = { "vim%.uv" } },
            },
        },
    },
}
