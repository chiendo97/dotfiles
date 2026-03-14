-- Load conform immediately (simple approach — it's lightweight)
vim.pack.add({ "https://github.com/stevearc/conform.nvim" })

require("conform").setup({
    formatters_by_ft = {
        lua = { "stylua" },
        python = { "isort", "black" },
        typst = { "typstfmt" },
        bash = { "shfmt" },
        zsh = { "shfmt" },
        go = { "gofumpt", "goimports", "golines" },
        yaml = { "yamlfmt" },
        ledger = { "hledger" },
        typescriptreact = { "eslint_d", "prettierd" },
        typescript = { "eslint_d", "prettierd" },
        json = { "fixjson", "jq", stop_after_first = true },
        markdown = { "rumdl" },
    },
    default_format_opts = {
        lsp_format = "fallback",
    },
    formatters = {
        rumdl = {
            command = "rumdl",
            args = { "fmt", "-", "-s", "-d", "MD025" },
            stdin = true,
        },
        shfmt = {
            prepend_args = { "-i", "2" },
        },
        hledger = {
            command = "hledger",
            args = { "-c", "1,000.0 vnd", "-c", "1,000.00 sgd", "-f-", "print" },
            stdin = true,
            require_cwd = false,
        },
        goimports = {
            prepend_args = { "-format-only" },
        },
        goline = {
            prepend_args = { "--base-formatter", "gofmt", "--shorten-comments" },
        },
    },
})

vim.keymap.set({ "n", "v", "x" }, "<leader>f", function()
    require("conform").format({ async = true })
end, { desc = "Format buffer" })

vim.o.formatexpr = "v:lua.require'conform'.formatexpr()"
