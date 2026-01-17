return {
    {
        "https://gitlab.com/motaz-shokry/gruvbox.nvim",
        name = "gruvbox",
        priority = 1000,
        config = function()
            require("gruvbox").setup({
                variant = "medium",
                dark_variant = "hard",
                dim_inactive_windows = true,
                extend_background_behind_borders = true,

                enable = {
                    terminal = true,
                    legacy_highlights = true,
                    migrations = true,
                    devicons = true,
                    lualine = true,
                },

                styles = {
                    bold = true,
                    italic = true,
                    transparency = false,
                },

                groups = {
                    border = "gray",
                    link = "purple_lite",
                    panel = "bg_second",

                    error = "red_lite",
                    hint = "aqua_lite",
                    info = "blue_lite",
                    ok = "green_lite",
                    warn = "yellow_lite",
                    note = "yellow_dark",
                    todo = "aqua_dark",

                    git_add = "green_dark",
                    git_change = "yellow_dark",
                    git_delete = "red_dark",
                    git_dirty = "orange_dark",
                    git_ignore = "gray",
                    git_merge = "purple_dark",
                    git_rename = "blue_dark",
                    git_stage = "purple_dark",
                    git_text = "yellow_lite",
                    git_untracked = "bg2",

                    h1 = "red_dark",
                    h2 = "yellow_dark",
                    h3 = "green_dark",
                    h4 = "aqua_dark",
                    h5 = "blue_dark",
                    h6 = "purple_dark",
                },

                highlight_groups = {

                    -- render-markdown
                    RenderMarkdownBullet = { fg = "green_dark" },
                    RenderMarkdownCode = { bg = "bg_second" },
                    RenderMarkdownCodeBorder = { bg = "bg1" },
                    RenderMarkdownTableHead = { fg = "purple_lite" },
                    RenderMarkdownTableRow = { fg = "purple_lite" },

                    -- Treesitter markup
                    ["@markup.heading"] = { fg = "green_dark" },
                    ["@markup.strong"] = { fg = "green_dark", bold = true },
                    ["@markup.italic"] = { fg = "green_dark", italic = true },
                },
            })
            vim.cmd.colorscheme("gruvbox")
        end,
    },
}
