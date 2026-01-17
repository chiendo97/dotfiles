---@diagnostic disable: param-type-mismatch

return {
    {
        "lewis6991/gitsigns.nvim",
        event = "VeryLazy",
        opts = {
            on_attach = function(bufnr)
                local gitsigns = require("gitsigns")

                local function map(mode, l, r, opts)
                    opts = opts or {}
                    opts.buffer = bufnr
                    vim.keymap.set(mode, l, r, opts)
                end

                -- Navigation
                map("n", "]h", function()
                    gitsigns.nav_hunk("next")
                end, { desc = "Go to next Git hunk" })

                map("n", "[h", function()
                    gitsigns.nav_hunk("prev")
                end, { desc = "Go to previous Git hunk" })

                -- Actions
                map("n", "ghs", gitsigns.stage_hunk, { desc = "Stage current hunk" })
                map("n", "ghr", gitsigns.reset_hunk, { desc = "Reset current hunk" })

                map("v", "ghs", function()
                    gitsigns.stage_hunk({ vim.fn.line("."), vim.fn.line("v") })
                end, { desc = "Stage selected hunks" })

                map("v", "ghr", function()
                    gitsigns.reset_hunk({ vim.fn.line("."), vim.fn.line("v") })
                end, { desc = "Reset selected hunks" })

                map("n", "ghS", gitsigns.stage_buffer, { desc = "Stage entire buffer" })
                map("n", "ghR", gitsigns.reset_buffer, { desc = "Reset entire buffer" })
                map("n", "ghp", gitsigns.preview_hunk, { desc = "Preview hunk" })
                map("n", "ghi", gitsigns.preview_hunk_inline, { desc = "Preview hunk inline" })

                map("n", "ghb", function()
                    gitsigns.blame_line({ full = true })
                end, { desc = "Show full git blame for current line" })

                map("n", "ghd", gitsigns.diffthis, { desc = "Diff this buffer against index" })

                map("n", "ghD", function()
                    gitsigns.diffthis("~")
                end, { desc = "Diff this buffer against last commit" })

                map("n", "ghQ", function()
                    gitsigns.setqflist("all")
                end, { desc = "Set quickfix list with all hunks" })
                map("n", "ghq", gitsigns.setqflist, { desc = "Set quickfix list with hunks" })

                -- Text object
                map({ "o", "x" }, "ih", gitsigns.select_hunk, { desc = "Select inner hunk" })
            end,
        },
    },
}
