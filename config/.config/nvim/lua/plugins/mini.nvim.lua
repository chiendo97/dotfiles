return {
    {
        "echasnovski/mini.nvim",
        dependencies = { "rafamadriz/friendly-snippets" },
        config = function()
            require("mini.statusline").setup({
                -- Content of statusline as functions which return statusline string. See
                -- `:h statusline` and code of default contents (used instead of `nil`).
                content = {
                    -- Content for active window
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

                        -- Usage of `MiniStatusline.combine_groups()` ensures highlighting and
                        -- correct padding with spaces between groups (accounts for 'missing'
                        -- sections, etc.)
                        return MiniStatusline.combine_groups({
                            { hl = mode_hl, strings = { mode } },
                            { hl = "MiniStatuslineFilename", strings = { filename } },
                            "%<", -- Mark general truncate point
                            { hl = "MiniStatuslineDevinfo", strings = { git, diff, diagnostics, lsp } },
                            "%=", -- End left alignment
                            { hl = "MiniStatuslineFileinfo", strings = { fileinfo } },
                            { hl = mode_hl, strings = { search, location } },
                        })
                    end,
                    -- Content for inactive window(s)
                    inactive = nil,
                },

                -- Whether to use icons by default
                use_icons = true,
            })
            -- Surround actions
            require("mini.surround").setup()
            -- Extend and create a/i textobjects
            require("mini.ai").setup({
                -- Number of lines within which textobject is searched
                n_lines = 50,

                -- How to search for object (first inside current line, then inside
                -- neighborhood). One of 'cover', 'cover_or_next', 'cover_or_prev',
                -- 'cover_or_nearest', 'next', 'prev', 'nearest'.
                search_method = "cover_or_nearest",

                -- Whether to disable showing non-error feedback
                -- This also affects (purely informational) helper messages shown after
                -- idle time if user input is required.
                silent = false,
            })
            require("mini.icons").setup() -- use default config
            require("mini.completion").setup({})

            require("mini.snippets").setup({
                snippets = {
                    require("mini.snippets").gen_loader.from_lang(),
                },
                -- Module mappings. Use `''` (empty string) to disable one.
                mappings = {
                    -- Expand snippet at cursor position. Created globally in Insert mode.
                    expand = "<C-j>",

                    -- Interact with default `expand.insert` session.
                    -- Created for the duration of active session(s)
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
                -- command = "lua vim.b.minicompletion_disable=true",
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
        end,
    },
}
