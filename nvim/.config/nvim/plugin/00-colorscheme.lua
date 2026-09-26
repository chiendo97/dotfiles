vim.pack.add({ "https://github.com/ember-theme/nvim" })

require("ember").setup({
    variant = "ember",
    on_highlights = function(hl, theme)
        -- Code block background
        hl.ColorColumn = { bg = theme.ui.base3 }

        -- Borders: brighten for visibility
        hl.FloatBorder = { fg = theme.ui.base5, bg = theme.ui.float_bg }
        hl.WinSeparator = { fg = theme.ui.base5 }

        -- Render-markdown: bullets, code, tables
        hl.RenderMarkdownBullet = { fg = theme.syn.sage }
        hl.RenderMarkdownCode = { bg = theme.ui.base2 }
        hl.RenderMarkdownCodeBorder = { bg = theme.ui.base1 }
        hl.RenderMarkdownTableHead = { fg = theme.syn.steel, bold = true }
        hl.RenderMarkdownTableRow = { fg = theme.syn.steel }

        -- Render-markdown: heading backgrounds (subtle tinted bands)
        hl.RenderMarkdownH1Bg = { bg = "#2b2220" }
        hl.RenderMarkdownH2Bg = { bg = "#2a2520" }
        hl.RenderMarkdownH3Bg = { bg = "#2a2822" }
        hl.RenderMarkdownH4Bg = { bg = "#252820" }
        hl.RenderMarkdownH5Bg = { bg = "#202528" }
        hl.RenderMarkdownH6Bg = { bg = "#252425" }

        -- Embedded SQL in Rust sqlx query strings
        hl["@sqlx.query"] = { bg = theme.ui.base2 }
        hl["@sqlx.query.rust"] = { bg = theme.ui.base2 }

        -- Sqmeow's drawer and grid use a cooler, higher-contrast palette.
        hl.SqmeowNormal = { fg = "#dce1df", bg = "#111619" }
        hl.SqmeowCursorLine = { bg = "#1b2228" }
        hl.SqmeowWinbar = { fg = "#e5e7e6", bg = "#111619", bold = true }
        hl.SqmeowHeader = { fg = "#e5e7e6", bg = "#1b2228", bold = true }
        hl.SqmeowRule = { fg = "#3a474e" }
        hl.SqmeowText = { fg = "#dce1df" }
        hl.SqmeowNumber = { fg = "#a8c9c7" }
        hl.SqmeowNull = { fg = "#758994", italic = true }
        hl.SqmeowMarker = { fg = "#758994" }
        hl.SqmeowExpression = { fg = "#dcc69e" }
        hl.SqmeowConnected = { fg = "#9fc7a5" }
        hl.SqmeowIconConnection = { fg = "#e0a0b5" }
        hl.SqmeowIconPostgres = { fg = "#8caed8" }
        hl.SqmeowIconSchema = { fg = "#dbc49a" }
        hl.SqmeowIconTable = { fg = "#79cde0" }
        hl.SqmeowIconView = { fg = "#bc9bd5" }
        hl.SqmeowIconColumn = { fg = "#79cde0" }
        hl.SqmeowIconFunction = { fg = "#9fc7a5" }
        hl.SqmeowIconProcedure = { fg = "#e0a0b5" }
        hl.SqmeowIconScratchpad = { fg = "#dbc49a" }
        hl.SqmeowIconHistory = { fg = "#9fc7a5" }
        hl.SqmeowIconKeyPrimary = { fg = "#dbc49a" }
        hl.SqmeowIconKeyForeign = { fg = "#9fc7a5" }
        hl.SqmeowIconTypeText = { fg = "#79cde0" }
        hl.SqmeowIconTypeNumber = { fg = "#a8c9c7" }
        hl.SqmeowIconTypeBoolean = { fg = "#df8293" }
        hl.SqmeowIconTypeTemporal = { fg = "#df8293" }
        hl.SqmeowIconTypeJson = { fg = "#dcc69e" }
        hl.SqmeowIconTypeUuid = { fg = "#9dbb9d" }
        hl.SqmeowIconTypeBinary = { fg = "#758994" }
    end,
})

vim.cmd.colorscheme("ember")
