vim.pack.add({
    "https://github.com/rafamadriz/friendly-snippets",
    "https://github.com/echasnovski/mini.nvim",
})

require("mini.statusline").setup({
    content = {
        active = function()
            local mode, mode_hl = MiniStatusline.section_mode({ trunc_width = 120 })
            local git = MiniStatusline.section_git({ trunc_width = 40 })
            local diff = MiniStatusline.section_diff({ trunc_width = 75 })
            local diagnostics = MiniStatusline.section_diagnostics({ trunc_width = 75 })
            local lsp = MiniStatusline.section_lsp({ trunc_width = 75 })
            local filename = "%{expand('%:~:.')!=#''?expand('%:~:.'):'[No Name]'}"
            local fileinfo = MiniStatusline.section_fileinfo({ trunc_width = 120 })
            local location = MiniStatusline.section_location({ trunc_width = 75 })
            local search = MiniStatusline.section_searchcount({ trunc_width = 75 })

            return MiniStatusline.combine_groups({
                { hl = mode_hl, strings = { mode } },
                { hl = "MiniStatuslineFilename", strings = { filename } },
                "%<",
                { hl = "MiniStatuslineDevinfo", strings = { git, diff, diagnostics, lsp } },
                "%=",
                { hl = "MiniStatuslineFileinfo", strings = { fileinfo } },
                { hl = mode_hl, strings = { search, location } },
            })
        end,
        inactive = nil,
    },
    use_icons = true,
})

require("mini.surround").setup()

require("mini.ai").setup({
    n_lines = 50,
    search_method = "cover_or_nearest",
    silent = false,
})

require("mini.icons").setup()
require("mini.completion").setup({})

require("mini.snippets").setup({
    snippets = {
        require("mini.snippets").gen_loader.from_lang(),
    },
    mappings = {
        expand = "<C-j>",
        jump_next = "<C-l>",
        jump_prev = "<C-h>",
        stop = "<C-e>",
    },
})

MiniSnippets.start_lsp_server()

vim.api.nvim_create_autocmd("FileType", {
    group = vim.api.nvim_create_augroup("user_mini", { clear = true }),
    pattern = { "snacks_picker_input", "snacks_input" },
    desc = "Disable mini.completion for snacks picker",
    callback = function()
        vim.b.minicompletion_disable = true
    end,
})

require("mini.cmdline").setup({})
require("mini.files").setup({})
require("mini.colors").setup({})

vim.keymap.set("n", "<leader>c", function()
    require("mini.files").open(vim.api.nvim_buf_get_name(0))
end, { desc = "Open MiniFiles" })

vim.api.nvim_create_autocmd("User", {
    pattern = "MiniFilesBufferCreate",
    callback = function(args)
        local buf_id = args.data.buf_id
        vim.keymap.set("n", "<leader>c", function()
            require("mini.files").close()
        end, {
            desc = "Close MiniFiles",
            buffer = buf_id,
        })
    end,
})
