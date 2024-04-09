local parser_config = require("nvim-treesitter.parsers").get_parser_configs()

parser_config.http = {
    install_info = {
        url = "https://github.com/NTBBloodbath/tree-sitter-http",
        files = { "src/parser.c" },
        branch = "main",
    },
}

require("rest-nvim").setup({
    result_split_horizontal = false,
    skip_ssl_verification = false,
    highlight = {
        enabled = true,
        timeout = 150,
    },
    jump_to_request = false,
})

vim.api.nvim_set_keymap("n", "<C-g>", "<Plug>RestNvim", {})
