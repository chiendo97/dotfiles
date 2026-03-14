vim.api.nvim_create_autocmd("FileType", {
    pattern = "http",
    once = true,
    callback = function()
        vim.pack.add({ "https://github.com/mistweaverco/kulala.nvim" })
        require("kulala").setup({
            ui = { split_direction = "horizontal" },
            default_view = "body",
        })
    end,
})
