if vim.env.NVIM ~= nil then
    print("Exiting with status 2")
    os.exit(2)
end

require("config.options")
-- require("config.statusline")
require("config.tabline")
require("config.keymaps")
require("config.autocmds")
require("config.path_picker").setup()

require("vim._core.ui2").enable({})
