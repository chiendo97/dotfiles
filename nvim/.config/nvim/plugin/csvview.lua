vim.api.nvim_create_autocmd("FileType", {
    pattern = { "csv", "tsv" },
    once = true,
    callback = function()
        vim.notify("Loading csvview.nvim...")
        vim.pack.add({ "https://github.com/hat0uma/csvview.nvim" })
        require("csvview").setup({
            view = { display_mode = "border" },
            parser = { comments = { "#", "//" } },
            keymaps = {
                textobject_field_inner = { "if", mode = { "o", "x" } },
                textobject_field_outer = { "af", mode = { "o", "x" } },
                jump_next_field_end = { "<Tab>", mode = { "n", "v" } },
                jump_prev_field_end = { "<S-Tab>", mode = { "n", "v" } },
                jump_next_row = { "<Enter>", mode = { "n", "v" } },
                jump_prev_row = { "<S-Enter>", mode = { "n", "v" } },
            },
            header_lnum = 1,
        })
    end,
})
