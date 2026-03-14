vim.api.nvim_create_autocmd("FileType", {
    pattern = { "markdown", "text", "txt" },
    once = true,
    callback = function()
        vim.pack.add({ "https://github.com/yousefhadder/markdown-plus.nvim" })
        require("markdown-plus").setup({
            enabled = true,
            features = {
                list_management = true,
                text_formatting = true,
                headers_toc = true,
                links = true,
            },
            keymaps = { enabled = true },
            filetypes = { "markdown", "text", "txt" },
        })
    end,
})
