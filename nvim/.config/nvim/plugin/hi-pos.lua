local pos

local function get_pos()
    if pos == nil then
        vim.pack.add({ "https://github.com/maxonvim/hi-pos.nvim" })
        pos = require("hi_pos").setup({
            filetypes = false,
            disable_uppercase_filenames = false,
        })
    end

    return pos
end

vim.api.nvim_create_autocmd("FileType", {
    pattern = "markdown",
    callback = function(event)
        get_pos().start(event.buf)
    end,
})

vim.api.nvim_create_user_command("HiPosStart", function(args)
    get_pos().start(args.buf)
end, { desc = "Start POS highlighting for the current buffer" })

vim.api.nvim_create_user_command("HiPosStop", function(args)
    get_pos().stop(args.buf)
end, { desc = "Stop POS highlighting for the current buffer" })

vim.api.nvim_create_user_command("HiPosToggle", function(args)
    get_pos().toggle(args.buf)
end, { desc = "Toggle POS highlighting for the current buffer" })
