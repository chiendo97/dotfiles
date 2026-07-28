vim.api.nvim_create_autocmd("FileType", {
    pattern = { "markdown", "codecompanion", "AgenticChat" },
    once = true,
    callback = function()
        vim.pack.add({ "https://github.com/MeanderingProgrammer/render-markdown.nvim" })
        require("render-markdown").setup({
            render_modes = { "n", "no", "c", "t", "i", "ic" },
            bullet = {
                icons = { "•", "◦", "▪", "▫" },
                ordered_icons = function(ctx)
                    return ("%d."):format(ctx.index)
                end,
            },
            checkbox = {
                enabled = true,
            },
            code = {
                sign = false,
                border = "thin",
                position = "left",
                width = "block",
                above = "─",
                below = "─",
                language_left = "╭─ ",
                language_right = " ─",
                language_border = "─",
                left_pad = 2,
                right_pad = 2,
                highlight_border = "RenderMarkdownCode",
            },
            heading = {
                width = "block",
                backgrounds = {
                    "MiniStatusLineModeNormal",
                    "MiniStatusLineModeInsert",
                    "MiniStatusLineModeReplace",
                    "MiniStatusLineModeVisual",
                    "MiniStatusLineModeCommand",
                    "MiniStatusLineModeOther",
                },
                sign = false,
                left_pad = 0,
                right_pad = 0,
                position = "right",
                icons = { "", "", "", "", "", "" },
            },
            dash = {
                icon = "─",
                width = "full",
            },
            quote = {
                icon = "┃",
            },
            pipe_table = {
                preset = "round",
                cell = "trimmed",
                alignment_indicator = "─",
                style = "full",
            },
        })
    end,
})
