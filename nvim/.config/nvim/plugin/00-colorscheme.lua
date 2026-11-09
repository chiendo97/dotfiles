vim.pack.add({ "https://github.com/Codesmith28/gruvbox_v2.nvim" })

vim.o.background = "light"
require("gruvbox_v2").setup({
    contrast = "medium",
    transparent = false,
    overrides = {
        ["@sqlx.query"] = { bg = "#f2e5bc" },
        ["@sqlx.query.rust"] = { bg = "#f2e5bc" },
    },
})

vim.cmd.colorscheme("gruvbox_v2")
