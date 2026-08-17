vim.api.nvim_create_autocmd("FileType", {
    pattern = { "markdown", "html" },
    once = true,
    callback = function()
        vim.pack.add({ "https://github.com/brianhuster/live-preview.nvim" })

        require("livepreview.config").set({
            address = "0.0.0.0",
            browser = "true",
            dynamic_root = true,
        })
    end,
})
