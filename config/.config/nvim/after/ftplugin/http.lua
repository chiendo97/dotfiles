vim.keymap.set("n", "<CR>", function()
    require("kulala").run()
end, { noremap = true, silent = true, desc = "Execute the request", buffer = true })

vim.keymap.set("n", "[[", function()
    require("kulala").jump_prev()
end, { noremap = true, silent = true, desc = "Jump to the previous request", buffer = true })

vim.keymap.set("n", "]]", function()
    require("kulala").jump_next()
end, { noremap = true, silent = true, desc = "Jump to the next request", buffer = true })

vim.keymap.set("n", "<leader>I", function()
    require("kulala").inspect()
end, { noremap = true, silent = true, desc = "Inspect the current request", buffer = true })

vim.keymap.set("n", "<leader>t", function()
    require("kulala").toggle_view()
end, { noremap = true, silent = true, desc = "Toggle between body and headers", buffer = true })

vim.keymap.set("n", "<leader>k", function()
    require("kulala").copy()
end, { noremap = true, silent = true, desc = "Copy the current request as a curl command", buffer = true })

vim.keymap.set("n", "<leader>p", function()
    require("kulala").set_selected_env()
end, { noremap = true, silent = true, desc = "Copy the current request as a curl command", buffer = true })
