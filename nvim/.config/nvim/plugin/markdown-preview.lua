vim.api.nvim_create_autocmd("FileType", {
    pattern = { "markdown" },
    once = true,
    callback = function()
        vim.pack.add({ "https://github.com/sammaji/markdown-preview.nvim" })

        -- listen on all interfaces (was address = "0.0.0.0" with live-preview)
        vim.g.mkdp_open_to_the_world = 1

        -- server only: no xdg-open, just print the URL
        vim.cmd([[
          function! MkdpNoBrowser(url)
            echo a:url
          endfunction
        ]])
        vim.g.mkdp_browserfunc = "MkdpNoBrowser"

        vim.keymap.set("n", "<leader>mp", "<cmd>MarkdownPreviewToggle<cr>", {
            desc = "Markdown preview (toggle)",
        })
    end,
})
