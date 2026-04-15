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
    end,
})

vim.cmd.colorscheme("ember")
