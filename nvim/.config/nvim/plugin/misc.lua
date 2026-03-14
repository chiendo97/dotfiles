-- Immediate-load plugins (small, no lazy trigger needed)
vim.pack.add({
    "https://github.com/j-hui/fidget.nvim",
    "https://github.com/mason-org/mason.nvim",
    "https://github.com/b0o/schemastore.nvim",
    "https://github.com/nvim-lua/plenary.nvim",
    "https://github.com/antonk52/filepaths_ls.nvim",
    "https://github.com/jrop/tuis.nvim",
})

require("fidget").setup({
    notification = {
        window = {
            border = "rounded",
            winblend = 0,
        },
    },
})

require("mason").setup()

-- Scheduled plugins (was event=VeryLazy or similar)
vim.schedule(function()
    vim.pack.add({
        "https://github.com/folke/todo-comments.nvim",
        "https://github.com/junegunn/vim-easy-align",
        "https://github.com/ruifm/gitlinker.nvim",
        "https://github.com/polacekpavel/prompt-yank.nvim",
    })

    require("todo-comments").setup({})

    vim.api.nvim_set_keymap("x", "ga", "<Plug>(EasyAlign)", {})
    vim.api.nvim_set_keymap("n", "ga", "<Plug>(EasyAlign)", {})

    require("gitlinker").setup({ mappings = "ghl" })

    require("prompt-yank").setup({
        keymaps = {
            copy_selection = "<Leader>ys",
            copy_file = "<Leader>ys",
        },
    })
end)

-- FileType-triggered plugins
vim.api.nvim_create_autocmd("FileType", {
    pattern = { "markdown", "codecompanion", "AgenticChat" },
    once = true,
    callback = function()
        vim.pack.add({ "https://github.com/MeanderingProgrammer/render-markdown.nvim" })
        require("render-markdown").setup({
            render_modes = { "n", "no", "c", "t", "i", "ic" },
            checkbox = {
                enable = true,
                position = "inline",
            },
            code = {
                sign = false,
                border = "thin",
                position = "right",
                width = "block",
                above = "▁",
                below = "▔",
                language_left = "█",
                language_right = "█",
                language_border = "▁",
                left_pad = 0,
                right_pad = 0,
            },
            heading = {
                width = "block",
                backgrounds = {
                    "MiniStatusLineModeNormal",
                    "MiniStatusLineModeInsert",
                    "MiniStatusLineModeReplace",
                    "MiniStatusLineModeVisual",
                    "MiniStatusLineModeCommand",
                    "MiniStatusLineModeOther",
                },
                sign = false,
                left_pad = 0,
                right_pad = 0,
                position = "right",
                icons = { "", "", "", "", "", "" },
            },
            pipe_table = { style = "normal" },
        })
    end,
})

vim.api.nvim_create_autocmd("FileType", {
    pattern = "lua",
    once = true,
    callback = function()
        vim.pack.add({ "https://github.com/folke/lazydev.nvim" })
        require("lazydev").setup({
            library = {
                { path = "${3rd}/luv/library", words = { "vim%.uv" } },
            },
        })
    end,
})

vim.api.nvim_create_autocmd("FileType", {
    pattern = "http",
    once = true,
    callback = function()
        vim.pack.add({ "https://github.com/mistweaverco/kulala.nvim" })
        require("kulala").setup({
            ui = { split_direction = "horizontal" },
            default_view = "body",
        })
    end,
})

vim.api.nvim_create_autocmd("FileType", {
    pattern = { "markdown", "text", "txt" },
    once = true,
    callback = function()
        vim.pack.add({ "https://github.com/yousefhadder/markdown-plus.nvim" })
        require("markdown-plus").setup({
            enabled = true,
            features = {
                list_management = true,
                text_formatting = true,
                headers_toc = true,
                links = true,
            },
            keymaps = { enabled = true },
            filetypes = { "markdown", "text", "txt" },
        })
    end,
})

vim.api.nvim_create_autocmd("FileType", {
    pattern = "qf",
    once = true,
    callback = function()
        vim.pack.add({ "https://github.com/kevinhwang91/nvim-bqf" })
    end,
})

vim.api.nvim_create_autocmd("FileType", {
    pattern = "csv",
    once = true,
    callback = function()
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

-- Command-triggered plugins
vim.api.nvim_create_user_command("StartupTime", function()
    vim.pack.add({ "https://github.com/tweekmonster/startuptime.vim" })
    vim.cmd("StartupTime")
end, { desc = "Profile startup time" })

vim.api.nvim_create_user_command("JqPlayground", function()
    vim.pack.add({ "https://github.com/yochem/jq-playground.nvim" })
    require("jq-playground").setup({ query_window = { scratch = true } })
    vim.cmd("JqPlayground")
end, { desc = "JQ Playground" })

vim.api.nvim_create_user_command("Cling", function(info)
    vim.pack.add({ "https://github.com/juniorsundar/cling.nvim" })
    require("cling").setup({
        wrappers = {
            { binary = "docker", command = "Docker", help_cmd = "--help" },
            {
                binary = "eza",
                command = "Eza",
                completion_file = "https://raw.githubusercontent.com/eza-community/eza/main/completions/bash/eza",
            },
        },
    })
    vim.cmd("Cling " .. (info.args or ""))
end, { desc = "Cling CLI wrapper", nargs = "*" })

vim.api.nvim_create_user_command("Calcium", function()
    vim.pack.add({ "https://github.com/necrom4/calcium.nvim" })
    require("calcium").setup({})
    vim.cmd("Calcium")
end, { desc = "Calcium calculator" })

vim.api.nvim_create_user_command("LivePreview", function()
    vim.pack.add({ "https://github.com/brianhuster/live-preview.nvim" })
    require("livepreview.config").set({
        port = 5500,
        browser = "default",
        dynamic_root = false,
        sync_scroll = true,
        picker = "vim.ui.select",
        address = "0.0.0.0",
    })
    vim.cmd("LivePreview")
end, { desc = "Live Preview" })

-- Conditional plugins
if vim.fn.executable("mcp-hub") == 1 then
    vim.pack.add({ "https://github.com/ravitemer/mcphub.nvim" })
    require("mcphub").setup({ auto_approve = true })
end
