-- Bootstrap packer
local install_path = vim.fn.stdpath("data") .. "/site/pack/packer/opt/packer.nvim"

if vim.fn.empty(vim.fn.glob(install_path)) > 0 then
    print("installing packer")
    vim.fn.execute("!git clone --depth 1 https://github.com/wbthomason/packer.nvim " .. install_path)
end

vim.cmd([[packadd packer.nvim]])

local map = vim.keymap.set
map("n", "<leader>pi", "<cmd>PackerInstall<cr>", { noremap = true, silent = true })
map("n", "<leader>ps", "<cmd>PackerSync<cr>", { noremap = true, silent = true })
map("n", "<leader>pc", "<cmd>PackerCompile<cr>", { noremap = true, silent = true })
map("n", "<leader>pt", "<cmd>PackerStatus<cr>", { noremap = true, silent = true })
map("n", "<leader>pd", "<cmd>PackerClean<cr>", { noremap = true, silent = true })

return require("packer").startup(function(use)
    -- Packer can manage itself as an optional plugin
    use({ "wbthomason/packer.nvim", opt = true })

    -- add packages
    use({
        "tweekmonster/startuptime.vim",
        cmd = "StartupTime",
    })

    use({ "nvim-lua/plenary.nvim" })

    -- nvim-tree
    use({
        "kyazdani42/nvim-tree.lua",
        requires = { "kyazdani42/nvim-web-devicons" },
        cmd = "NvimTreeToggle",
        setup = function()
            vim.keymap.set("n", "<leader>c", "<cmd>NvimTreeToggle<cr>", { noremap = true })
        end,
        config = function()
            require("plugins.nvim-tree")
        end,
    })

    -- lspconfig
    use({
        "neovim/nvim-lspconfig",
        config = function()
            require("lsp")
        end,
    })

    -- lsp autocomplete
    use({
        "hrsh7th/nvim-cmp",
        requires = {
            "hrsh7th/cmp-nvim-lsp", -- lsp source
            "hrsh7th/cmp-vsnip", -- vsnip source
            "hrsh7th/vim-vsnip", -- snippet engine
            "hrsh7th/cmp-buffer",
        },
        config = function()
            require("plugins.nvim-cmp")
        end,
    })

    -- go vscode snippet
    use({
        "rafamadriz/friendly-snippets",
        ft = {
            "go",
            "plaintex",
        },
    })

    -- add brackets
    use({ "machakann/vim-sandwich" })

    -- linter, formater
    use({
        "jose-elias-alvarez/null-ls.nvim",
        config = function()
            require("lsp.null-ls")
        end,
        requires = {
            "nvim-lua/plenary.nvim",
            "neovim/nvim-lspconfig",
        },
    })

    -- note manager
    use({
        "nvim-orgmode/orgmode",
        config = function()
            require("plugins.orgmode")
        end,
    })

    -- treesitter syntax
    use({
        "nvim-treesitter/nvim-treesitter",
        run = ":TSUpdate",
        config = function()
            require("plugins.treesitter")
        end,
    })

    -- Comment code
    use({
        "numToStr/Comment.nvim",
        config = function()
            require("plugins.Comment")
        end,
    })

    -- align text with ga=
    use({
        "junegunn/vim-easy-align",
        config = function()
            -- Start interactive EasyAlign in visual mode (e.g. vipga)
            vim.api.nvim_set_keymap("x", "ga", "<Plug>(EasyAlign)", {})
            -- Start interactive EasyAlign for a motion/text object (e.g. gaip)
            vim.api.nvim_set_keymap("n", "ga", "<Plug>(EasyAlign)", {})
        end,
    })

    -- Preview markdown live: :MarkdownPreview
    use({
        "iamcco/markdown-preview.nvim",
        run = "cd app && yarn install",
        ft = "markdown",
        setup = function()
            vim.g.mkdp_filetypes = { "markdown" }
        end,
        cmd = "MarkdownPreview",
    })

    -- Add git related info in the signs columns and popups
    use({
        "lewis6991/gitsigns.nvim",
        requires = { "nvim-lua/plenary.nvim" },
        config = function()
            require("plugins.gitsigns")
        end,
        cond = function()
            return vim.fn.isdirectory(".git") == 1
        end,
    })

    -- vim-tmux-navigation
    use({
        "christoomey/vim-tmux-navigator",
        config = function()
            vim.g.tmux_navigator_disable_when_zoomed = 1
        end,
    })

    -- colorscheme https://www.reddit.com/r/neovim/comments/nkqkdy/gruvbox_flat_colorscheme_written_in_lua_with/
    use({
        "eddyekofo94/gruvbox-flat.nvim",
        config = function()
            -- Example config in Lua
            vim.g.gruvbox_italic_functions = true
            vim.g.gruvbox_sidebars = { "qf", "vista_kind", "terminal", "packer" }

            -- Change the "hint" color to the "orange" color, and make the "error" color bright red
            vim.g.gruvbox_colors = { hint = "orange", error = "#ff0000" }

            -- Change the TabLineSel highlight group (used by barbar.nvim) to the "orange" color
            vim.g.gruvbox_theme = { TabLineSel = { bg = "orange" } }
            vim.g.gruvbox_flat_style = "dark"

            -- Load the colorscheme
            vim.cmd([[colorscheme gruvbox-flat]])
        end,
    })

    use({
        "nvim-telescope/telescope.nvim",
        cmd = "Telescope",
        setup = function()
            require("plugins.telescope_map")
        end,
        config = function()
            require("plugins.telescope")
        end,
        requires = {
            { "nvim-lua/plenary.nvim" },
            { "nvim-telescope/telescope-fzf-native.nvim", run = "make" },
        },
    })

    -- generate go test
    use({
        "buoto/gotests-vim",
        ft = "go",
        cmd = "GoTests",
    })

    -- better quickfix
    use({
        "kevinhwang91/nvim-bqf",
        config = function()
            require("plugins.nvim-bqf")
        end,
        ft = "qf",
    })

    use({
        "lukas-reineke/indent-blankline.nvim",
        config = function()
            require("plugins.indent-blankline")
        end,
    })

    use({
        vim.fn.stdpath("config") .. "/lua/go-tag",
        config = function()
            require("go-tag")
        end,
        ft = "go",
    })

    use({
        "NTBBloodbath/rest.nvim",
        requires = { "nvim-lua/plenary.nvim" },
        ft = "http",
        config = function()
            require("plugins.rest")
        end,
    })

    use({
        "chrisbra/csv.vim",
        ft = "csv",
        config = function() end,
    })

    -- nvim-treesitter/playground
    -- use({
    --     "nvim-treesitter/playground",
    -- })
end)
