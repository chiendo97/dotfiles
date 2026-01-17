---@diagnostic disable: param-type-mismatch

local my_augroup = vim.api.nvim_create_augroup("cle.autocmd", { clear = true })

vim.api.nvim_create_autocmd("FileType", {
    group = my_augroup,
    pattern = "qf",
    callback = function()
        vim.api.nvim_cmd({ cmd = "wincmd", args = { "J" } }, {})
    end,
    desc = "Move quickfix window to the bottom",
})

vim.api.nvim_create_autocmd("BufReadPost", {
    group = my_augroup,
    pattern = "*",
    callback = function()
        local line = vim.fn.line("'\"")
        if
            line > 1
            and line <= vim.fn.line("$")
            and vim.bo.filetype ~= "commit"
            and vim.bo.filetype ~= "help"
            and vim.bo.filetype ~= "snacks_picker_list"
            and vim.fn.index({ "xxd", "gitrebase" }, vim.bo.filetype) == -1
        then
            vim.cmd('normal! g`"')
        end
    end,
    desc = "Jump to the last edited line in the buffer",
})

-- Highlight when yanking (copying) text
--  Try it with `yap` in normal mode
--  See `:help vim.highlight.on_yank()`
vim.api.nvim_create_autocmd("TextYankPost", {
    group = my_augroup,
    desc = "Highlight when yanking (copying) text",
    callback = function()
        vim.highlight.on_yank()
    end,
})

vim.api.nvim_create_autocmd("VimEnter", {
    group = my_augroup,
    callback = function()
        require("lazy").update({ show = false })
    end,
    desc = "Update lazy plugins silently on VimEnter",
})

-- Consolidated FileType autocmd for treesitter features
vim.api.nvim_create_autocmd("FileType", {
    group = my_augroup,
    pattern = "*",
    callback = function()
        local ft = vim.bo.filetype
        local lang = vim.treesitter.language.get_lang(ft)

        if not lang or not vim.treesitter.language.add(lang) then
            return
        end

        vim.treesitter.start()

        -- Set folding if available
        if vim.treesitter.query.get(lang, "folds") then
            vim.wo.foldexpr = "v:lua.vim.treesitter.foldexpr()"
            vim.wo.foldmethod = "expr"
        end
    end,
})

vim.api.nvim_create_autocmd("VimEnter", {
    group = my_augroup,
    callback = function()
        vim.cmd("clearjumps")
    end,
    desc = "Clear jump list on VimEnter",
})

vim.api.nvim_create_user_command("T", function()
    vim.cmd(":sp term://zsh")
    vim.cmd("startinsert")
end, {})

vim.api.nvim_create_user_command("VT", function()
    vim.cmd(":vsp term://zsh")
    vim.cmd("startinsert")
end, {})

vim.api.nvim_create_user_command("R", function(opts)
    -- Expand % and # BEFORE opening new buffer
    local current = vim.fn.expand("%:p")
    local alt = vim.fn.expand("#:p")
    local cmd = opts.args:gsub("%%:p", current):gsub("%%", current):gsub("#", alt)
    vim.cmd("new")
    vim.bo.buftype = "nofile"
    vim.bo.bufhidden = "hide"
    vim.bo.swapfile = false
    vim.b.no_auto_close = true
    vim.fn.termopen(cmd, {
        on_stdout = function()
            vim.schedule(function()
                vim.cmd("normal! G")
            end)
        end,
    })
    vim.api.nvim_buf_set_keymap(0, "n", "q", ":q!<CR>", { noremap = true, silent = true })
end, { nargs = "+", complete = "shellcmd" })
