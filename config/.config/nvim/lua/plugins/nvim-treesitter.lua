return {
    {
        "nvim-treesitter/nvim-treesitter",
        branch = "main",
        config = function()
            -- You can use the capture groups defined in `textobjects.scm`
            local ts_select = require("nvim-treesitter-textobjects.select")
            local ts_move = require("nvim-treesitter-textobjects.move")

            local function map_textobject(modes, key, capture, query_group, desc)
                vim.keymap.set(modes, key, function()
                    ts_select.select_textobject(capture, query_group or "textobjects")
                end, { desc = desc })
            end

            local textobjects = {
                { key = "af", capture = "@function.outer", query_group = nil, desc = "[TS] Select outer function" },
                { key = "if", capture = "@function.inner", query_group = nil, desc = "[TS] Select inner function" },
                { key = "ac", capture = "@class.outer", query_group = nil, desc = "[TS] Select outer class" },
                { key = "ic", capture = "@class.inner", query_group = nil, desc = "[TS] Select inner class" },
                { key = "as", capture = "@local.scope", query_group = "locals", desc = "[TS] Select local scope" },
            }

            for _, obj in ipairs(textobjects) do
                map_textobject({ "x", "o" }, obj.key, obj.capture, obj.query_group, obj.desc)
            end

            -- configuration
            require("nvim-treesitter-textobjects").setup({
                move = {
                    -- whether to set jumps in the jumplist
                    set_jumps = true,
                },
            })

            local next_start_moves = {
                { key = "]f", capture = "@function.outer", query_group = "textobjects", desc = "[TS] Next fn start" },
                { key = "]c", capture = "@class.outer", query_group = "textobjects", desc = "[TS] Next class start" },
            }

            local next_end_moves = {
                { key = "]F", capture = "@function.outer", query_group = "textobjects", desc = "[TS] Next fn end" },
                { key = "]C", capture = "@class.outer", query_group = "textobjects", desc = "[TS] Next class end" },
            }

            local previous_start_moves = {
                { key = "[f", capture = "@function.outer", query_group = "textobjects", desc = "[TS] Prev fn start" },
                { key = "[c", capture = "@class.outer", query_group = "textobjects", desc = "[TS] Prev class start" },
            }

            local previous_end_moves = {
                { key = "[F", capture = "@function.outer", query_group = "textobjects", desc = "[TS] Prev fn end" },
                { key = "[C", capture = "@class.outer", query_group = "textobjects", desc = "[TS] Prev class end" },
            }

            for _, obj in ipairs(next_start_moves) do
                vim.keymap.set({ "n", "x", "o" }, obj.key, function()
                    ts_move.goto_next_start(obj.capture, obj.query_group)
                end, { silent = true, desc = obj.desc })
            end

            for _, obj in ipairs(next_end_moves) do
                vim.keymap.set({ "n", "x", "o" }, obj.key, function()
                    ts_move.goto_next_end(obj.capture, obj.query_group)
                end, { silent = true, desc = obj.desc })
            end

            for _, obj in ipairs(previous_start_moves) do
                vim.keymap.set({ "n", "x", "o" }, obj.key, function()
                    ts_move.goto_previous_start(obj.capture, obj.query_group)
                end, { silent = true, desc = obj.desc })
            end

            for _, obj in ipairs(previous_end_moves) do
                vim.keymap.set({ "n", "x", "o" }, obj.key, function()
                    ts_move.goto_previous_end(obj.capture, obj.query_group)
                end, { silent = true, desc = obj.desc })
            end
        end,
        dependencies = {
            { "nvim-treesitter/nvim-treesitter-textobjects", branch = "main" },
        },
    },
}
