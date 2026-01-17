-- vim.lsp.set_log_level("debug")
-- require("vim.lsp.log").set_format_func(vim.inspect)

-- vim.api.nvim_create_autocmd("LspProgress", {
--     group = vim.api.nvim_create_augroup("lsp_progress", { clear = true }),
--     ---@param ev {data: {client_id: integer, params: lsp.ProgressParams}}
--     callback = function(ev)
--         local spinner = { "⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏" }
--         vim.notify(vim.lsp.status(), vim.log.levels.INFO, {
--             id = "lsp_progress",
--             title = "LSP Progress",
--             opts = function(notif)
--                 notif.icon = ev.data.params.value.kind == "end" and " "
--                     or spinner[math.floor(vim.uv.hrtime() / (1e6 * 80)) % #spinner + 1]
--             end,
--         })
--     end,
-- })

local api, lsp, keymap = vim.api, vim.lsp, vim.keymap

vim.diagnostic.config({
    float = {
        format = function(diagnostic)
            return string.format("%s (%s)", diagnostic.message, diagnostic.source)
        end,
    },
    jump = {
        float = true,
    },
})

api.nvim_create_autocmd("LspAttach", {
    group = api.nvim_create_augroup("cle.lsp.config", { clear = true }),
    callback = function(args)
        local client = assert(lsp.get_client_by_id(args.data.client_id))
        local bufnr = args.buf

        local _opts = function(desc)
            return {
                nowait = true,
                noremap = true,
                silent = true,
                buffer = bufnr,
                desc = "LSP " .. desc,
            }
        end

        local toggle_diagnostic = function()
            local buffnr_opts = { bufnr = bufnr }
            vim.diagnostic.enable(not vim.diagnostic.is_enabled(buffnr_opts), buffnr_opts)
        end

        local diagnostic_qflist = function()
            vim.diagnostic.setqflist({
                open = true,
                format = function(diagnostic)
                    -- print(bufnr, vim.inspect(diagnostic))
                    if diagnostic.bufnr ~= bufnr then
                        return nil
                    end
                    return string.format("%s (%s)", diagnostic.message, diagnostic.source)
                end,
            })
        end

        keymap.set("n", "gD", lsp.buf.declaration, _opts("Go to declaration"))
        keymap.set("n", "gd", lsp.buf.definition, _opts("Go to definition"))
        keymap.set("n", "gr", lsp.buf.references, _opts("Go to references"))
        keymap.set("n", "K", lsp.buf.hover, _opts("Hover for info"))
        keymap.set("n", "gi", lsp.buf.implementation, _opts("Go to implementation"))
        keymap.set("n", "gy", lsp.buf.type_definition, _opts("Go to type definition"))
        keymap.set("n", "<leader>e", lsp.buf.rename, _opts("Rename symbol"))
        keymap.set("n", "<leader>a", lsp.buf.code_action, _opts("Show code actions"))
        keymap.set("n", "<leader>q", diagnostic_qflist, _opts("Set quickfix list"))
        keymap.set("n", "<leader>Q", toggle_diagnostic, _opts("Toggle diagnostics"))

        if client.server_capabilities.inlayHintProvider then
            lsp.inlay_hint.enable(true)
        end

        if client.server_capabilities.inlineCompletionProvider then
            lsp.inline_completion.enable(true)

            keymap.set("i", "<c-g>", function()
                if not vim.lsp.inline_completion.get() then
                    return false
                end
                return true
            end, {
                remap = true,
                desc = "Accept the current inline completion",
                buffer = bufnr,
            })
        end
    end,
})

-- Global capabilities for all servers
local is_blink, blink_cmp = pcall(require, "blink.cmp")
local capabilities = is_blink and blink_cmp.get_lsp_capabilities() or lsp.protocol.make_client_capabilities()

-- Define configurations
lsp.config("*", {
    capabilities = capabilities,
    root_markers = { ".git" },
})

-- Configure individual servers
local lsp_servers = {
    "basedpyright",
    "bashls",
    "copilot",
    "dartls",
    "gopls",
    "jsonls",
    "lua_ls",
    -- "markdown_oxide",
    "ruff",
    "rust_analyzer",
    "sourcekit",
    "tinymist",
    -- "ts_ls",
    "tsgo",
    "zls",
    -- "pyrefly",
    -- "ty",
}

for _, server in ipairs(lsp_servers) do
    lsp.enable(server)
end

-- Remove default global keymaps
keymap.del("n", "grr")
keymap.del("n", "gri")
keymap.del("n", "gra")
keymap.del("n", "grn")

-- Called from plugin/lspconfig.vim because it requires knowing that the last
-- script in scriptnames to be executed is lspconfig.
api.nvim_create_user_command("LspInfo", ":checkhealth vim.lsp", { desc = "Alias to `:checkhealth vim.lsp`" })

api.nvim_create_user_command("LspLog", function()
    vim.cmd.edit(lsp.log.get_filename())
end, {
    desc = "Opens the Nvim LSP client log.",
})

if vim.fn.has("nvim-0.11.2") == 1 then
    local complete_client = function(arg)
        return vim.iter(lsp.get_clients())
            :map(function(client)
                return client.name
            end)
            :filter(function(name)
                return name:sub(1, #arg) == arg
            end)
            :totable()
    end

    local complete_config = function(arg)
        return vim.iter(api.nvim_get_runtime_file(("lsp/%s*.lua"):format(arg), true))
            :map(function(path)
                local file_name = path:match("[^/]*.lua$")
                return file_name:sub(0, #file_name - 4)
            end)
            :totable()
    end

    api.nvim_create_user_command("LspStart", function(info)
        local servers = info.fargs

        -- Default to enabling all servers matching the filetype of the current buffer.
        -- This assumes that they've been explicitly configured through `lsp.config`,
        -- otherwise they won't be present in the private `lsp.config._configs` table.
        if #servers == 0 then
            return
        end

        lsp.enable(servers)
    end, {
        desc = "Enable and launch a language server",
        nargs = "?",
        complete = complete_config,
    })

    api.nvim_create_user_command("LspRestart", function(info)
        local client_names = info.fargs

        -- Default to restarting all active servers
        if #client_names == 0 then
            client_names = vim.iter(lsp.get_clients())
                :map(function(client)
                    return client.name
                end)
                :totable()
        end

        for name in vim.iter(client_names) do
            if lsp.config[name] == nil then
                vim.notify(("Invalid server name '%s'"):format(name))
            else
                lsp.enable(name, false)
                if info.bang then
                    vim.iter(lsp.get_clients({ name = name })):each(function(client)
                        client:stop(true)
                    end)
                end
            end
        end

        local timer = assert(vim.uv.new_timer())
        timer:start(500, 0, function()
            for name in vim.iter(client_names) do
                vim.schedule_wrap(lsp.enable)(name)
            end
        end)
    end, {
        desc = "Restart the given client",
        nargs = "?",
        bang = true,
        complete = complete_client,
    })

    api.nvim_create_user_command("LspStop", function(info)
        local client_names = info.fargs

        -- Default to disabling all servers on current buffer
        if #client_names == 0 then
            client_names = vim.iter(lsp.get_clients())
                :map(function(client)
                    return client.name
                end)
                :totable()
        end

        for name in vim.iter(client_names) do
            if lsp.config[name] == nil then
                vim.notify(("Invalid server name '%s'"):format(name))
            else
                lsp.enable(name, false)
                if info.bang then
                    vim.iter(lsp.get_clients({ name = name })):each(function(client)
                        client:stop(true)
                    end)
                end
            end
        end
    end, {
        desc = "Disable and stop the given client",
        nargs = "?",
        bang = true,
        complete = complete_client,
    })

    return
end
