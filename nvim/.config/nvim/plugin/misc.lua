-- Small plugins that don't warrant their own file
vim.pack.add({
    "https://github.com/b0o/schemastore.nvim",
    "https://github.com/nvim-lua/plenary.nvim",
    "https://github.com/antonk52/filepaths_ls.nvim",
    "https://github.com/jrop/tuis.nvim",
})

vim.schedule(function()
    vim.pack.add({
        "https://github.com/ruifm/gitlinker.nvim",
        "https://github.com/polacekpavel/prompt-yank.nvim",
    })

    require("gitlinker").setup({ mappings = "ghl" })

    require("prompt-yank").setup({
        keymaps = {
            copy_selection = "<Leader>ys",
            copy_file = "<Leader>ys",
        },
    })
end)

-- FileType: quickfix
vim.api.nvim_create_autocmd("FileType", {
    pattern = "qf",
    once = true,
    callback = function()
        vim.pack.add({ "https://github.com/kevinhwang91/nvim-bqf" })
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
