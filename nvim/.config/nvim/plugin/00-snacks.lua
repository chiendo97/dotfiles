vim.pack.add({ "https://github.com/folke/snacks.nvim" })

require("snacks").setup({
    bigfile = { enabled = true },
    notifier = { enabled = true },
    indent = {
        enabled = true,
        char = "|",
        only_scope = true,
        only_current = true,
        animate = { enabled = false },
        scope = { enabled = false },
    },
    quickfile = { enabled = true },
    picker = {
        ui_select = true,
        win = {
            input = {
                keys = {
                    ["C-c"] = { "cancel", mode = { "i", "n" } },
                    ["<Esc>"] = { "close", mode = { "n", "i" } },
                    ["<c-u>"] = { "preview_scroll_up", mode = { "i", "n" } },
                    ["<c-d>"] = { "preview_scroll_down", mode = { "i", "n" } },
                    ["<c-y>"] = { "yank", mode = { "i", "n" } },
                },
            },
        },
    },
    styles = {
        help = {
            border = "rounded",
        },
        notification = {
            relative = "editor",
            wo = {
                wrap = true,
            },
        },
    },
})

-- Snacks picker keymaps
vim.keymap.set("n", "<leader>t", function()
    require("snacks.picker").notifications({ win = { preview = { wo = { wrap = true } } } })
end, { desc = "Show notification history" })

vim.keymap.set("n", "<leader>g", function()
    require("snacks.picker").files()
end, { desc = "Find files" })

vim.keymap.set("n", "<leader>r", function()
    require("snacks.picker").grep()
end, { desc = "Live grep" })

vim.keymap.set("x", "<leader>r", function()
    require("snacks.picker").grep_word()
end, { desc = "Grep selection" })

vim.keymap.set("n", "<leader>R", function()
    require("snacks.picker").grep_word()
end, { desc = "Grep word under cursor" })

vim.keymap.set("n", "<leader>h", function()
    require("snacks.picker").help()
end, { desc = "Help tags" })

vim.keymap.set("n", "<leader>j", function()
    require("snacks.picker").recent({ filter = { cwd = true } })
end, { desc = "Recent files" })

vim.keymap.set("n", "<leader>m", function()
    require("snacks.picker").keymaps()
end, { desc = "Keymaps" })

vim.keymap.set("n", "<leader>n", function()
    require("snacks.picker").resume()
end, { desc = "Resume last search" })

vim.keymap.set("n", "<leader>b", function()
    require("snacks.picker").pickers()
end, { desc = "Snacks builtins" })

vim.keymap.set("n", "<leader>S", function()
    require("snacks.picker").lsp_symbols()
end, { desc = "LSP symbols" })

vim.keymap.set("n", "<leader>s", function()
    require("snacks.picker").spelling()
end, { desc = "Spell suggest" })

vim.keymap.set("n", "<leader>i", function()
    require("snacks.picker").command_history({
        sort = function(a, b)
            return a.idx < b.idx
        end,
    })
end, { desc = "Command history" })
