return {
    {
        "alexghergh/nvim-tmux-navigation",
        event = "VeryLazy",
        config = function()
            local nvim_tmux_nav = require("nvim-tmux-navigation")

            nvim_tmux_nav.setup({
                disable_when_zoomed = true,
            })

            vim.keymap.set("n", "<C-h>", nvim_tmux_nav.NvimTmuxNavigateLeft)
            vim.keymap.set("n", "<C-j>", nvim_tmux_nav.NvimTmuxNavigateDown)
            vim.keymap.set("n", "<C-k>", nvim_tmux_nav.NvimTmuxNavigateUp)
            vim.keymap.set("n", "<C-l>", nvim_tmux_nav.NvimTmuxNavigateRight)

            vim.keymap.set("t", "<C-h>", nvim_tmux_nav.NvimTmuxNavigateLeft)
            vim.keymap.set("t", "<C-j>", nvim_tmux_nav.NvimTmuxNavigateDown)
            vim.keymap.set("t", "<C-k>", nvim_tmux_nav.NvimTmuxNavigateUp)
            vim.keymap.set("t", "<C-l>", nvim_tmux_nav.NvimTmuxNavigateRight)
        end,
    },
}
