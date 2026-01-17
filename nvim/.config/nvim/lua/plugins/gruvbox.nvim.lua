return {
    {
        "ellisonleao/gruvbox.nvim",
        priority = 1000,
        config = function()
            local palette = require("gruvbox").palette
            require("gruvbox").setup({
                terminal_colors = true,
                undercurl = true,
                underline = true,
                bold = true,
                italic = {
                    strings = true,
                    emphasis = true,
                    comments = true,
                    operators = false,
                    folds = true,
                },
                strikethrough = true,
                invert_selection = false,
                invert_signs = false,
                invert_tabline = false,
                invert_intend_guides = false,
                inverse = true,
                contrast = "hard",
                palette_overrides = {},
                dim_inactive = false,
                transparent_mode = false,
                overrides = {
                    -- Leap
                    LeapBackdrop = { fg = palette.dark4 },
                    LeapLabel = { fg = palette.bright_orange, bold = true },

                    -- MiniPick
                    MiniPickMatchRanges = { fg = palette.bright_green, bold = true },

                    -- MiniTabline
                    MiniTablineCurrent = { fg = palette.bright_blue, bg = palette.dark0_hard, bold = true },
                    MiniTablineHidden = { fg = palette.gray, bg = palette.dark1 },
                    MiniTablineModifiedCurrent = { fg = palette.dark0_hard, bg = palette.bright_blue, bold = true },
                    MiniTablineModifiedHidden = { fg = palette.dark0_hard, bg = palette.gray },
                    MiniTablineModifiedVisible = { fg = palette.dark0_hard, bg = palette.gray, bold = true },
                    MiniTablineTabpagesection = { fg = palette.dark0_hard, bg = palette.bright_aqua, bold = true },
                    MiniTablineVisible = { fg = palette.gray, bg = palette.dark1, bold = true },

                    -- MiniHipatterns
                    MiniHipatternsFixme = { fg = palette.dark0, bg = palette.bright_red },
                    MiniHipatternsFixmeBody = { fg = palette.bright_red },
                    MiniHipatternsFixmeColon = { fg = palette.bright_red, bg = palette.bright_red, bold = true },
                    MiniHipatternsHack = { fg = palette.dark0, bg = palette.bright_yellow },
                    MiniHipatternsHackBody = { fg = palette.bright_yellow },
                    MiniHipatternsHackColon = { fg = palette.bright_yellow, bg = palette.bright_yellow, bold = true },
                    MiniHipatternsNote = { fg = palette.dark0, bg = palette.bright_blue },
                    MiniHipatternsNoteBody = { fg = palette.bright_blue },
                    MiniHipatternsNoteColon = { fg = palette.bright_blue, bg = palette.bright_blue, bold = true },
                    MiniHipatternsTodo = { fg = palette.dark0, bg = palette.bright_green },
                    MiniHipatternsTodoBody = { fg = palette.bright_green },
                    MiniHipatternsTodoColon = { fg = palette.bright_green, bg = palette.bright_green, bold = true },

                    -- MiniStatusline
                    MiniStatuslineDirectory = { fg = palette.dark4, bg = palette.dark1 },
                    MiniStatuslineFilename = { fg = palette.light1, bg = palette.dark1, bold = true },
                    MiniStatuslineFilenameModified = { fg = palette.bright_blue, bg = palette.dark1, bold = true },
                    MiniStatuslineInactive = { fg = palette.dark4, bg = palette.dark1 },
                    MiniStatuslineDevinfo = { fg = palette.light2, bg = palette.dark2 },
                    MiniStatuslineFileinfo = { fg = palette.light2, bg = palette.dark2 },

                    -- MiniJump2d
                    MiniJump2dDim = { fg = palette.dark4 },
                    MiniJump2dSpot = { fg = palette.bright_orange, bg = palette.dark0_hard, bold = true },
                    MiniJump2dSpotUnique = { fg = palette.bright_orange, bg = palette.dark0_hard, bold = true },
                    MiniJump2dSpotAhead = { fg = palette.bright_yellow, bg = palette.dark0_hard },

                    -- RenderMarkdown
                    RenderMarkdownH1Bg = { bg = palette.faded_red },
                    RenderMarkdownH2Bg = { bg = palette.faded_orange },
                    RenderMarkdownH3Bg = { bg = palette.faded_yellow },
                    RenderMarkdownH4Bg = { bg = palette.faded_green },
                    RenderMarkdownH5Bg = { bg = palette.faded_blue },
                    RenderMarkdownH6Bg = { bg = palette.faded_purple },

                    RenderMarkdownCodeBorder = { bg = palette.dark2 },
                    RenderMarkdownCode = { bg = palette.dark0_soft },
                    RenderMarkdownTableHead = { fg = palette.dark3 },
                    RenderMarkdownTableRow = { fg = palette.dark3 },
                    RenderMarkdownBullet = { fg = palette.bright_green },

                    -- TreesitterContext
                    TreesitterContext = { bg = palette.dark0_soft },
                    TreesitterContextLineNumber = { fg = palette.dark4, bg = palette.dark0_soft },
                    TreesitterContextBottom = { underline = true, sp = palette.dark1 },
                },
            })
            vim.o.background = "dark"
            -- vim.cmd.colorscheme("gruvbox")
        end,
    },
}
