return {
    {
        "nvim-orgmode/orgmode",
        enabled = false,
        dependencies = {
            "nvim-orgmode/org-bullets.nvim",
        },
        event = "VeryLazy",
        config = function()
            -- Load custom tree-sitter grammar for org filetype
            require("orgmode").setup({
                org_agenda_files = "/Users/chiendo97/Library/CloudStorage/Dropbox/org/**/*",
                org_default_notes_file = "/Users/chiendo97/Library/CloudStorage/Dropbox/org/inbox.org",
                -- org_hide_leading_stars = true,
                -- org_ellipsis = "", -- hide marker used to indicate a folded headline.
                org_blank_before_new_entry = {
                    heading = false,
                    plain_list_item = false,
                },
                org_deadline_warning_days = 5,
                org_agenda_span = "week",
                org_agenda_skip_scheduled_if_done = true,
                org_agenda_skip_deadline_if_done = true,
                org_todo_keywords = { "TODO(t)", "NEXT(n)", "|", "DONE(d)" },
                win_split_mode = "float",
                mappings = {
                    org = {
                        org_todo = "ct",
                        org_todo_prev = "cT",
                        org_return = {},
                    },
                },
                org_startup_folded = "overview",
            })
            require("org-bullets").setup()
        end,
    },
}
