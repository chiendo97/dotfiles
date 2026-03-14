local sidekick_loaded = false

local function ensure_sidekick()
    if sidekick_loaded then
        return
    end
    vim.pack.add({ "https://github.com/folke/sidekick.nvim" })
    require("sidekick").setup({
        nes = { enabled = false },
        copilot = { status = { enabled = false } },
    })
    sidekick_loaded = true
end

vim.keymap.set({ "x", "n" }, "<leader>at", function()
    ensure_sidekick()
    require("sidekick.cli").send({ msg = "{this}" })
end, { desc = "Send This" })

vim.keymap.set("n", "<leader>af", function()
    ensure_sidekick()
    require("sidekick.cli").send({ msg = "{file}" })
end, { desc = "Send File" })

vim.keymap.set("x", "<leader>av", function()
    ensure_sidekick()
    require("sidekick.cli").send({ msg = "{selection}" })
end, { desc = "Send Visual Selection" })

vim.keymap.set("n", "<leader>la", function()
    ensure_sidekick()
    require("sidekick.cli").toggle({ name = "claude", focus = true })
end, { desc = "Sidekick Toggle Claude" })
