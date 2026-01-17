vim.opt_local.shiftwidth = 2
vim.opt_local.tabstop = 2
vim.opt_local.softtabstop = 2
vim.opt_local.expandtab = true

vim.opt_local.foldmethod = "indent" -- fold based on indent level

-- Format selected text with jq command
vim.keymap.set("x", "<leader>j", ":!jq<cr>", { noremap = true, desc = "Format selected text with jq" })
