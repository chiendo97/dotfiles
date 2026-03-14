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
-- config.lsp is loaded from plugin/zz-lsp.lua (after vim.pack plugins are available)
