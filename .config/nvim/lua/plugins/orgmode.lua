-- Load custom tree-sitter grammar for org filetype
require("orgmode").setup_ts_grammar()

require("orgmode").setup({
    org_agenda_files = "~/Dropbox/org/*",
    org_default_notes_file = "~/Dropbox/org/inbox.org",
    org_hide_leading_stars = true,
    org_ellipsis = "", -- hide marker used to indicate a folded headline.
    org_blank_before_new_entry = {
        heading = false,
        plain_list_item = false,
    },
    org_deadline_warning_days = 5,
    org_agenda_span = "week",
    org_agenda_skip_scheduled_if_done = true,
    org_agenda_skip_deadline_if_done = true,
})
