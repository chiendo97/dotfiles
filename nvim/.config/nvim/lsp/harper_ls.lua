return {
    cmd = { "harper-ls", "--stdio" },
    filetypes = { "markdown", "text", "tex", "typst" },
    settings = {
        ["harper-ls"] = {
            linters = {
                SentenceCapitalization = false,
            },
        },
    },
}
