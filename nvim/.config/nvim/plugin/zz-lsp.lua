-- Load LSP config after all plugins are available
-- (must run after misc.lua which loads schemastore.nvim etc.)
require("config.lsp")
