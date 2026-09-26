vim.pack.add({
	"https://github.com/MunifTanjim/nui.nvim",
	"https://github.com/2giosangmitom/sqmeow.nvim",
})

-- Install the engine binary only if missing. `install()` unconditionally
-- re-downloads, so the guard matters. `:Sqmeow install` re-runs it manually;
-- `:Sqmeow install cargo` builds from source instead.
if not require("sqmeow.install").resolve() then
	require("sqmeow").install()
end

-- Toggle the sqmeow UI (drawer + open windows).
-- Everything else (connect, scratchpad, grid nav) uses the plugin's
-- built-in keymaps inside the drawer — see `?` there or the cheatsheet.
vim.keymap.set("n", "<leader>d", "<cmd>Sqmeow toggle<cr>", { desc = "Db: toggle drawer + results" })