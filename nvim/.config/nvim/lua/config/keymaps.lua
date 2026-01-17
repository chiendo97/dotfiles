-- Leader key as space
vim.g.mapleader = " "

-- Backspace to switch to the most recent file
vim.keymap.set("n", "<bs>", "<c-^>", { noremap = true, desc = "Switch to recent file" })

-- Alt + jk to move line up/down
vim.keymap.set("n", "<A-j>", ":m .+1<cr>==", { noremap = true, silent = true, desc = "Move line down" })
vim.keymap.set("n", "<A-k>", ":m .-2<cr>==", { noremap = true, silent = true, desc = "Move line up" })
vim.keymap.set(
    "i",
    "<A-j>",
    "<Esc>:m .+1<cr>==gi",
    { noremap = true, silent = true, desc = "Move line down (insert mode)" }
)
vim.keymap.set(
    "i",
    "<A-k>",
    "<Esc>:m .-2<cr>==gi",
    { noremap = true, silent = true, desc = "Move line up (insert mode)" }
)
vim.keymap.set("x", "<A-j>", ":m '>+1<cr>gv=gv", { noremap = true, silent = true, desc = "Move block down" })
vim.keymap.set("x", "<A-k>", ":m '<-2<cr>gv=gv", { noremap = true, silent = true, desc = "Move block up" })

-- ^ - jump to the first non-blank character of the line
vim.keymap.set("n", "H", "g^", { noremap = true, desc = "Jump to first non-blank" })
vim.keymap.set("x", "H", "g^", { noremap = true, desc = "Jump to first non-blank" })

-- g_ - jump to the end of the line
vim.keymap.set("n", "L", "g$", { noremap = true, desc = "Jump to end of line" })
vim.keymap.set("x", "L", "g_", { noremap = true, desc = "Jump to end of line" })

-- Ctrl + c to turn off highlight and close quickfix windows and escape
-- vim.keymap.set("n", "<C-C>", ":noh<cr>:ccl<cr><esc>", { noremap = true, silent = true })
vim.keymap.set("n", "<C-C>", function()
    vim.cmd.noh()
    vim.cmd.ccl()
end, {
    noremap = true,
    silent = true,
    desc = "Clear search highlight and close quickfix window",
})
-- vim.keymap.set("i", "<C-C>", "<esc>", { noremap = true, silent = true })
-- vim.keymap.set("n", "<esc>", ":noh<cr>:ccl<cr><esc>", { noremap = true, silent = true })

-- * to highlight current word
vim.keymap.set(
    "n",
    "*",
    [[:let @/ = '\<'.expand('<cword>').'\>' | set hlsearch <cr>]],
    { silent = true, desc = "Highlight current word" }
)

-- To highlight currently selected word
vim.keymap.set("x", [[/]], [[y/\V<C-R>=escape(@",'/\')<cr><cr>]], { noremap = true, desc = "Highlight selected word" })
-- vim.keymap.set("x", "/", '"vy/<C-r>v<cr>', { noremap = true, desc = "Search for visually selected text" })

-- Navigate between tabs
vim.keymap.set("n", "gt", ":tabedit<cr>", { noremap = true, silent = true, desc = "Open new tab" })
vim.keymap.set("n", "gn", "<cmd>tabnext<cr>", { noremap = true, silent = true, desc = "Next tab" })
vim.keymap.set("n", "gp", "<cmd>tabprev<cr>", { noremap = true, silent = true, desc = "Previous tab" })
vim.keymap.set("n", "g1", "1gt", { noremap = true, silent = true, desc = "Go to tab 1" })
vim.keymap.set("n", "g2", "2gt", { noremap = true, silent = true, desc = "Go to tab 2" })
vim.keymap.set("n", "g3", "3gt", { noremap = true, silent = true, desc = "Go to tab 3" })
vim.keymap.set("n", "g4", "4gt", { noremap = true, silent = true, desc = "Go to tab 4" })
vim.keymap.set("n", "g5", "5gt", { noremap = true, silent = true, desc = "Go to tab 5" })
vim.keymap.set("n", "g6", "6gt", { noremap = true, silent = true, desc = "Go to tab 6" })
vim.keymap.set("n", "g7", "7gt", { noremap = true, silent = true, desc = "Go to tab 7" })
vim.keymap.set("n", "g8", "8gt", { noremap = true, silent = true, desc = "Go to tab 8" })
vim.keymap.set("n", "g9", "9gt", { noremap = true, silent = true, desc = "Go to tab 9" })

-- Move up/down without breaking column
vim.keymap.set("n", "j", "gj", { noremap = true, silent = true, desc = "Down with line wraps" })
vim.keymap.set("n", "k", "gk", { noremap = true, silent = true, desc = "Up with line wraps" })
vim.keymap.set("x", "j", "gj", { noremap = true, silent = true, desc = "Down with line wraps" })
vim.keymap.set("x", "k", "gk", { noremap = true, silent = true, desc = "Up with line wraps" })

-- Copy to system's clipboard
vim.keymap.set("x", "y", '"*y', { noremap = true, desc = "Yank to clipboard" })
vim.keymap.set("x", "p", '"+p', { noremap = true, desc = "Paste from last Yank" })
vim.keymap.set("n", "yy", '"*yy', { noremap = false, desc = "Yank line to clipboard" })

-- Copy current relative path
vim.keymap.set("n", "<leader>yp", ':let @* = expand("%:~:.")<cr>', { noremap = true, desc = "Yank relative path" })

-- Copy current absolute path
vim.keymap.set("n", "<leader>yP", ':let @* = expand("%:p")<cr>', { noremap = true, desc = "Yank absolute path" })

-- Copy last pasted
vim.keymap.set("n", "gV", "`[v`]", { noremap = true, desc = "Select last pasted region" })

-- Terminal mode escape
vim.keymap.set("t", "<esc>", "<cmd>stopinsert<cr>", { noremap = true, desc = "Escape terminal mode" })

-- Toggle line wrapping
vim.keymap.set("n", "<leader>W", ":set wrap!<CR>", { noremap = true, silent = true, desc = "Toggle wrap" })

-- Resize window commands
vim.keymap.set("n", "=", "<cmd>vertical resize +5<CR>", { noremap = true, desc = "Increase vertical size" })
vim.keymap.set("n", "-", "<cmd>vertical resize -5<CR>", { noremap = true, desc = "Decrease vertical size" })
vim.keymap.set("n", "+", "<cmd>horizontal resize +2<CR>", { noremap = true, desc = "Increase horizontal size" })
vim.keymap.set("n", "_", "<cmd>horizontal resize -2<CR>", { noremap = true, desc = "Decrease horizontal size" })

-- Run lua code in normal mode
vim.keymap.set("n", "<leader><space>x", "<cmd>source %<CR>", { noremap = true, desc = "Source current file" })
vim.keymap.set("n", "<leader>x", ":.lua<CR>", { noremap = true, desc = "Execute current line as Lua" })
vim.keymap.set("v", "<leader>x", ":lua<CR>", { noremap = true, desc = "Execute selected text as Lua" })

-- Duplicate a line and comment out the first line
vim.keymap.set("n", "yc", "<cmd>norm yygccp<cr>", { noremap = true, desc = "Duplicate line and comment original" })

-- From the Vim wiki: https://bit.ly/4eLAARp
-- Search and replace word under the cursor
vim.keymap.set(
    "n",
    "<leader>e",
    [[:%s/\<<C-r><C-w>\>//g<Left><Left>]],
    { noremap = true, desc = "Search & replace word under cursor" }
)

-- Sort selected text
vim.keymap.set("x", "<leader>s", ":sort<cr>", { noremap = true, desc = "Sort selected text" })
vim.keymap.set("x", "<leader>j", ":!fixjson<cr>", { noremap = true, desc = "Sort selected text" })

vim.keymap.set("x", "g/", "<C-\\><C-n>`</\\%V", { desc = "Search forward within visual selection" })
vim.keymap.set("x", "g?", "<C-\\><C-n>`>?\\%V", { desc = "Search backward within visual selection" })
