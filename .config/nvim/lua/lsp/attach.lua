local M = {}

vim.lsp.handlers["textDocument/hover"] = vim.lsp.with(vim.lsp.handlers.hover, { border = "single" })
vim.lsp.handlers["textDocument/signatureHelp"] = vim.lsp.with(vim.lsp.handlers.signature_help, { border = "single" })

local goto_next_diagnositc = function()
    return vim.diagnostic.goto_next({ float = { border = "single" } })
end

local goto_prev_diagnositc = function()
    return vim.diagnostic.goto_prev({ float = { border = "single" } })
end

local buf_format = function()
    return vim.lsp.buf.format({ timeout_ms = 2000 })
end

M.on_attach = function(_, bufnr)
    local opts = { noremap = true, silent = true, buffer = bufnr }

    vim.keymap.set("n", "gD", vim.lsp.buf.declaration, opts)
    vim.keymap.set("n", "gd", vim.lsp.buf.definition, opts)
    vim.keymap.set("n", "gr", vim.lsp.buf.references, opts)
    vim.keymap.set("n", "K", vim.lsp.buf.hover, opts)
    vim.keymap.set("n", "gi", vim.lsp.buf.implementation, opts)
    vim.keymap.set("n", "gy", vim.lsp.buf.type_definition, opts)
    vim.keymap.set("n", "<leader>e", vim.lsp.buf.rename, opts)
    vim.keymap.set("n", "<leader>f", buf_format, opts)
    vim.keymap.set("n", "[d", goto_prev_diagnositc, opts)
    vim.keymap.set("n", "]d", goto_next_diagnositc, opts)
    vim.keymap.set("n", "<leader>a", vim.lsp.buf.code_action, opts)
    vim.keymap.set("n", "<leader>q", vim.diagnostic.setloclist, opts)
end

M.capabilities = require("cmp_nvim_lsp").update_capabilities(vim.lsp.protocol.make_client_capabilities())

return M
