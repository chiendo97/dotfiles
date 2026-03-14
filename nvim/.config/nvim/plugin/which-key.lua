vim.schedule(function()
    vim.pack.add({ "https://github.com/folke/which-key.nvim" })
    require("which-key").setup({
        preset = "helix",
        delay = 300,
        triggers = {
            { "<auto>", mode = "nixsotc" },
        },
    })

    vim.keymap.set("n", "<leader>?", function()
        require("which-key").show({ global = false })
    end, { desc = "Buffer Local Keymaps (which-key)" })
end)
