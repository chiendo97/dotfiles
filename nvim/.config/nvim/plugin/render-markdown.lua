vim.api.nvim_create_autocmd("FileType", {
    pattern = { "markdown", "codecompanion", "AgenticChat" },
    once = true,
    callback = function()
        vim.pack.add({
            "https://github.com/MeanderingProgrammer/render-markdown.nvim",
            "https://github.com/ice345/markdown-table-wrap.nvim",
        })
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
        require("markdown-table-wrap").setup({
            auto_preview = false,
            highlight_preset = "default",
            inline_viewport_scrolling = false,
            preview_mode = "inline",
        })
    end,
})

vim.api.nvim_create_autocmd("FileType", {
    pattern = "markdown",
    callback = function(args)
        if vim.b[args.buf].markdown_table_wrap_reader then
            return
        end
        vim.keymap.set("n", "<localleader>tp", "<cmd>MarkdownTableFloatPreview<cr>", {
            buffer = args.buf,
            desc = "Preview Markdown table",
        })
    end,
})
