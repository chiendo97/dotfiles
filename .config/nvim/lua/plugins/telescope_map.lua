local packer = require("packer")

local map = vim.api.nvim_set_keymap
local set = vim.keymap.set

local map_options = { noremap = true, silent = true }

local load_telescope = function()
    if not pcall(require, "telescope") then
        packer.loader("plenary.nvim")
        packer.loader("telescope-fzf-native.nvim")
        packer.loader("telescope.nvim")
    end
end

local grep_cword = function()
    load_telescope()
    require("telescope.builtin").grep_string({ search = vim.fn.expand("<cword>") })
end

local grep_visual = function()
    local _, csrow, cscol, cerow, cecol
    local mode = vim.fn.mode()
    if mode == "v" or mode == "V" or mode == "" then
        -- if we are in visual mode use the live position
        _, csrow, cscol, _ = unpack(vim.fn.getpos("."))
        _, cerow, cecol, _ = unpack(vim.fn.getpos("v"))
        if mode == "V" then
            -- visual line doesn't provide columns
            cscol, cecol = 0, 999
        end
        -- exit visual mode
        vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Esc>", true, false, true), "n", true)
    else
        -- otherwise, use the last known visual position
        _, csrow, cscol, _ = unpack(vim.fn.getpos("'<"))
        _, cerow, cecol, _ = unpack(vim.fn.getpos("'>"))
    end
    -- swap vars if needed
    if cerow < csrow then
        csrow, cerow = cerow, csrow
    end
    if cecol < cscol then
        cscol, cecol = cecol, cscol
    end
    local lines = vim.fn.getline(csrow, cerow)
    local n = #lines
    if n <= 0 then
        return ""
    end
    lines[n] = string.sub(lines[n], 1, cecol)
    lines[1] = string.sub(lines[1], cscol)

    dump(csrow, cscol, cerow, cecol, lines)

    load_telescope()
    require("telescope.builtin").grep_string({ search = table.concat(lines, "\n") })
end

map("n", "<leader>g", [[<cmd>Telescope find_files <cr>]], map_options)
map("n", "<leader>r", [[<cmd>Telescope live_grep  <cr>]], map_options)
map("n", "<leader>h", [[<cmd>Telescope help_tags  <cr>]], map_options)
map("n", "<leader>j", [[<cmd>Telescope oldfiles only_cwd=true<cr>]], map_options)
map("n", "<leader>m", [[<cmd>Telescope keymaps    <cr>]], map_options)
map("n", "<leader>b", [[<cmd>Telescope builtin    <cr>]], map_options)

set("x", "<leader>r", grep_visual)
set("n", "<leader>R", grep_cword)
