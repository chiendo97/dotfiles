vim.pack.add({ "https://github.com/Codesmith28/gruvbox_v2.nvim" })

-- Leave background unset so Neovim follows the terminal appearance.
require("gruvbox_v2").setup({
    contrast = "medium",
    transparent = false,
})

vim.api.nvim_create_autocmd("ColorScheme", {
    pattern = "gruvbox_v2",
    callback = function()
        local bg = vim.o.background == "light" and "#f2e5bc" or "#3c3836"
        vim.api.nvim_set_hl(0, "@sqlx.query", { bg = bg })
        vim.api.nvim_set_hl(0, "@sqlx.query.rust", { bg = bg })
    end,
})

vim.cmd.colorscheme("gruvbox_v2")
