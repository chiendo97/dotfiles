vim.api.nvim_create_autocmd("FileType", {
    pattern = { "markdown", "codecompanion", "AgenticChat" },
    once = true,
    callback = function()
        vim.pack.add({ "https://github.com/MeanderingProgrammer/render-markdown.nvim" })
        require("render-markdown").setup({
            render_modes = { "n", "no", "c", "t", "i", "ic" },
            checkbox = {
                enable = true,
                position = "inline",
            },
            code = {
                sign = false,
                border = "thin",
                position = "right",
                width = "block",
                above = "▁",
                below = "▔",
                language_left = "█",
                language_right = "█",
                language_border = "▁",
                left_pad = 0,
                right_pad = 0,
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
            pipe_table = { style = "normal" },
        })
    end,
})
