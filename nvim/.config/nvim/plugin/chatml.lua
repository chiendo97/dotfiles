-- chatml.nvim (dev plugin from ~/Source/demo)
local dev_path = vim.fn.expand("~/Source/demo")
local chatml_path = dev_path .. "/chatml.nvim"

if vim.fn.isdirectory(chatml_path) == 1 then
    vim.opt.runtimepath:prepend(chatml_path)

    -- Source plugin scripts
    local plugin_scripts = vim.fn.glob(chatml_path .. "/plugin/**/*.lua", false, true)
    for _, script in ipairs(plugin_scripts) do
        vim.cmd.source(script)
    end

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
end
