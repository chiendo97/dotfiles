-- Dev plugins loaded from ~/Source/demo
local dev_path = vim.fn.expand("~/Source/demo")

local function dev_add(plugin_dir)
    local path = dev_path .. "/" .. plugin_dir
    if vim.fn.isdirectory(path) == 1 then
        vim.opt.runtimepath:prepend(path)
        -- Source plugin/ scripts manually
        local plugin_scripts = vim.fn.glob(path .. "/plugin/**/*.lua", false, true)
        for _, script in ipairs(plugin_scripts) do
            vim.cmd.source(script)
        end
    end
end

dev_add("morph.nvim")
dev_add("db-nbook.nvim")
dev_add("tmux-buffer.nvim")
