local loaded = false

local function ensure_chatml()
    if loaded then
        return
    end
    loaded = true
    -- fidget must be loaded before chatml (depends on fidget.progress)
    vim.pack.add({ "https://github.com/j-hui/fidget.nvim" })
    vim.pack.add({
        { src = "https://github.com/chiendo97/chatml.nvim", version = "cle/mcp" },
    })
    require("chatml").setup({})
end

vim.keymap.set("n", "<leader>lc", function()
    ensure_chatml()
    require("chatml/chat").new_chat()
end, { desc = "Create new chatml chat" })

vim.keymap.set("n", "<leader>lp", function()
    ensure_chatml()
    require("chatml/chat").picker()
end, { desc = "Picker chatml chat" })

vim.keymap.set("n", "<leader>lg", function()
    ensure_chatml()
    require("chatml/chat").search()
end, { desc = "Search chatml chat" })
