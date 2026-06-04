vim.pack.add({ "https://github.com/r4ppz/lspeek.nvim" })

local lspeek = require("lspeek")

lspeek.setup({
    window = {
        width = 70,
        height = 15,
        border = "single",
    },
    stack_limit = 5,
    select_first = false,
    keymaps = {
        close = "q",
        split = "s",
        vsplit = "v",
        enter = "<CR>",
    },
})

vim.keymap.set("n", "gD", function()
    lspeek.peek_definition()
end, { desc = "Peek Definition (lspeek)" })

vim.keymap.set("n", "gT", function()
    lspeek.peek_type_definition()
end, { desc = "Peek Type Definition (lspeek)" })
