-- General settings
vim.g.mapleader = " " -- Use `<Space>` as a leader key
vim.o.mouse = "a" -- Enable mouse
vim.o.mousescroll = "ver:25,hor:6" -- Customize mouse scroll
vim.o.switchbuf = "usetab" -- Use already opened buffers when switching
vim.o.exrc = true -- Enable local vimrc files

-- UI settings
vim.o.showtabline = 2 -- Always show tab line
vim.o.ruler = true
vim.o.number = true
vim.o.cursorline = true
vim.wo.signcolumn = "yes"
vim.o.winborder = "rounded"
if vim.fn.has("nvim-0.12") == 1 then
    vim.o.pumborder = "rounded"
end
vim.o.showmode = false -- Don't show mode in command line
vim.o.laststatus = 3 -- Global statusline (3 = always show global)
vim.o.cmdheight = 2 -- Height of command line (number of lines)
vim.o.wrap = false
vim.wo.signcolumn = "yes" -- Always show sign column (for git, diagnostics, etc.)
vim.o.showmatch = true -- Always show matching brackets

-- Completion settings
vim.o.pumheight = 10
vim.o.completeopt = "menuone,noselect,nosort"
vim.o.wildmenu = true
vim.o.wildmode = "noselect,full"
vim.o.wildoptions = "pum,fuzzy"

-- Indentation settings
vim.o.tabstop = 2
vim.o.shiftwidth = 2
vim.o.expandtab = true

-- List characters - visual indicators for whitespace
vim.opt.list = true -- Show invisible characters
vim.opt.listchars = {
    tab = "│ ", -- Show tabs as │ followed by space
    eol = "↴", -- Show end of line as ↴
    trail = "·", -- Show trailing spaces as ·
    extends = "→", -- Show line continuation as →
}

-- Window splitting
vim.o.splitbelow = true
vim.o.splitright = true

-- Folding
vim.o.foldlevel = 99
vim.o.foldtext = "" -- Show text under fold with its highlighting
vim.opt.fillchars:append({ fold = " " })

-- File handling
vim.o.undofile = true -- Enable persistent undo
vim.o.backup = false
vim.o.writebackup = false
vim.o.swapfile = false

-- Search settings
vim.o.hlsearch = true
vim.o.incsearch = true
vim.o.ignorecase = true
vim.o.smartcase = true
vim.o.inccommand = "nosplit"

-- Grep settings
if vim.fn.executable("rg") == 1 then
    vim.o.grepprg = "rg --vimgrep --no-heading --smart-case --hidden"
    vim.o.grepformat = "%f:%l:%c:%m"
end

-- Clipboard configuration
if vim.env.TMUX ~= nil then
    vim.g.clipboard = "tmux"
else
    vim.g.clipboard = "osc52"
end
