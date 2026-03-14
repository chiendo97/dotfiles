-- fidget must be loaded before chatml (depends on fidget.progress)
vim.pack.add({ "https://github.com/j-hui/fidget.nvim" })
vim.pack.add({
    { src = "https://github.com/chiendo97/chatml.nvim", version = "cle/mcp" },
})

require("chatml").setup({})

vim.keymap.set("n", "<leader>lc", function()
    require("chatml/chat").new_chat()
end, { desc = "Create new chatml chat" })

vim.keymap.set("n", "<leader>lp", function()
    require("chatml/chat").picker()
end, { desc = "Picker chatml chat" })

vim.keymap.set("n", "<leader>lg", function()
    require("chatml/chat").search()
end, { desc = "Search chatml chat" })
