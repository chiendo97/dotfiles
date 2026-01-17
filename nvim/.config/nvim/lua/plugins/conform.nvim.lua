return {
    {
        "stevearc/conform.nvim",
        event = { "BufWritePre" },
        cmd = { "ConformInfo" },
        keys = {
            {
                -- Customize or remove this keymap to your liking
                "<leader>f",
                function()
                    require("conform").format({ async = true })
                end,
                mode = { "n", "v", "x" },
                desc = "Format buffer",
            },
        },
        config = function()
            require("conform").setup({
                -- Define your formatters
                formatters_by_ft = {
                    lua = { "stylua" },
                    python = { "isort", "black" },
                    typst = { "typstfmt" },
                    bash = { "shfmt" },
                    zsh = { "shfmt" },
                    go = { "gofumpt", "goimports", "golines" },
                    yaml = { "yamlfmt" },
                    ledger = { "hledger" },
                    -- javascript = { "prettierd", "prettier", stop_after_first = true },
                    typescriptreact = { "eslint_d", "prettierd" },
                    typescript = { "eslint_d", "prettierd" },
                    json = { "fixjson", "jq", stop_after_first = true },
                    markdown = { "rumdl" },
                },
                -- Set default options
                default_format_opts = {
                    -- LSP formatting is used when no other formatters are available
                    -- lsp_format = "fallback",
                    -- LSP formatting is used when available and then other formatters
                    lsp_format = "fallback",
                },
                -- Customize formatters
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
                        -- This can be a string or a function that returns a string.
                        -- When defining a new formatter, this is the only field that is required
                        command = "hledger",
                        -- A list of strings, or a function that returns a list of strings
                        -- Return a single string instead of a list to run the command in a shell
                        args = {
                            "-c",
                            "1,000.0 vnd",
                            "-c",
                            "1,000.00 sgd",
                            "-f-",
                            "print",
                        },
                        -- Send file contents to stdin, read new contents from stdout (default true)
                        -- When false, will create a temp file (will appear in "$FILENAME" args). The temp
                        -- file is assumed to be modified in-place by the format command.
                        stdin = true,
                        -- When cwd is not found, don't run the formatter (default false)
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

            -- vim.o.formatexpr = "v:lua.require'conform'.formatexpr()"
        end,
        init = function()
            -- If you want the formatexpr, here is the place to set it
            vim.o.formatexpr = "v:lua.require'conform'.formatexpr()"
        end,
    },
}
