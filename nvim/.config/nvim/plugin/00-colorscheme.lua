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

        -- sqmeow.nvim: the result grid colors only numbers/NULLs/headers by default,
        -- so a text-heavy table looks flat. Add a header band, a brighter text body,
        -- and colored type icons to match the README look.
        hl.SqmeowHeader = { fg = theme.ui.base8, bg = theme.ui.base3, bold = true }
        hl.SqmeowText = { fg = theme.ui.fg }
        hl.SqmeowNumber = { fg = theme.syn.number }
        hl.SqmeowNull = { fg = theme.ui.base6, italic = true }
        hl.SqmeowExpression = { fg = theme.syn.gold }
        hl.SqmeowIconTypeText = { fg = theme.syn.sage }
        hl.SqmeowIconTypeNumber = { fg = theme.syn.steel }
        hl.SqmeowIconTypeBoolean = { fg = theme.syn.coral }
        hl.SqmeowIconTypeTemporal = { fg = theme.syn.orange }
        hl.SqmeowIconTypeJson = { fg = theme.syn.gold }
        hl.SqmeowIconTypeUuid = { fg = theme.syn.mauve }
        hl.SqmeowIconTypeBinary = { fg = theme.syn.rose }
    end,
})

vim.cmd.colorscheme("ember")
