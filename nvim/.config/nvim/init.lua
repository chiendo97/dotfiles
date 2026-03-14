if vim.env.NVIM ~= nil then
    print("Exiting with status 2")
    os.exit(2)
end

require("config.options")
require("config.statusline")
require("config.tabline")
require("config.keymaps")
require("config.autocmds")
require("config.path_picker").setup()

-- Install hooks (must be registered before any vim.pack.add() in plugin/ files)
vim.api.nvim_create_autocmd("PackChanged", {
    callback = function(ev)
        local name, kind = ev.data.spec.name, ev.data.kind
        if name == "nvim-treesitter" and kind == "update" then
            if not ev.data.active then
                vim.cmd.packadd("nvim-treesitter")
            end
            vim.cmd("TSUpdate")
        end
    end,
})

-- config.lsp is loaded from plugin/zz-lsp.lua (after vim.pack plugins are available)
