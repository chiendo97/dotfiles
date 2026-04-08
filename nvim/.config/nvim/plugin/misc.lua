-- Small plugins that don't warrant their own file
vim.pack.add({
    "https://github.com/b0o/schemastore.nvim",
    "https://github.com/nvim-lua/plenary.nvim",
    "https://github.com/jrop/tuis.nvim",
    { src = "https://github.com/chiendo97/filepaths_ls.nvim", version = "use-cwd-instead-of-buf-dir" },
})

vim.schedule(function()
    vim.pack.add({
        "https://github.com/ruifm/gitlinker.nvim",
        "https://github.com/polacekpavel/prompt-yank.nvim",
    })

    require("gitlinker").setup({
        mappings = "ghl",
        callbacks = {
            ["git.urieljsc.com"] = require("gitlinker.hosts").get_gitlab_type_url,
        },
    })

    require("prompt-yank").setup({
        keymaps = {
            copy_selection = "<Leader>ys",
            copy_file = "<Leader>ys",
        },
    })
end)

-- quickfix: nvim-bqf
vim.pack.add({ "https://github.com/kevinhwang91/nvim-bqf" })

-- Filetype-triggered plugins
vim.api.nvim_create_autocmd("FileType", {
    pattern = { "markdown" },
    once = true,
    callback = function()
        vim.pack.add({ "https://github.com/zk-org/zk-nvim" })
        require("zk").setup({
            picker = "snacks_picker",
            lsp = {
                -- zk LSP is already managed via lsp/zk.lua + vim.lsp.enable
                config = { cmd = { "zk", "lsp" } },
                auto_attach = { enabled = false },
            },
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

