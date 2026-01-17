--[[
Path picker for `Neovim`.

## Usage

```lua
require("config.path_picker").setup()
```

You can then hit `<leader>p` to pick a file path.
- In normal mode: copies the path to clipboard
- In visual mode: replaces selected text with the path
]]
local path_picker = {}

---@class path_picker.config
path_picker.config = {
    keymap = "<leader>p",
}

--- Get all files in the current working directory recursively.
---@return string[]
local function get_files()
    local files = {}
    local cwd = vim.fn.getcwd()

    -- Use vim.fs.find with a predicate to get all files
    local found = vim.fs.find(function(name, path)
        local full_path = path .. "/" .. name
        local stat = vim.uv.fs_stat(full_path)
        return stat and stat.type == "file"
    end, {
        path = cwd,
        limit = math.huge,
        type = "file",
    })

    for _, file in ipairs(found) do
        -- Make path relative to cwd
        local relative = vim.fn.fnamemodify(file, ":.")
        table.insert(files, relative)
    end

    table.sort(files)
    return files
end

--- Pick a file and execute callback with the selected path.
---@param callback fun(path: string)
local function pick_file(callback)
    local files = get_files()

    if #files == 0 then
        vim.api.nvim_echo({
            { " 󰾕 path_picker.lua ", "DiagnosticVirtualTextWarn" },
            { ": ", "@comment" },
            { "No files found in current directory", "@comment" },
        }, true, {})
        return
    end

    vim.ui.select(files, {
        prompt = "Select file path:",
        format_item = function(item)
            return item
        end,
    }, function(selected)
        if selected then
            callback(selected)
        end
    end)
end

--- Copy path to clipboard (normal mode behavior).
local function copy_path_to_clipboard()
    pick_file(function(path)
        vim.fn.setreg("+", path)
        vim.fn.setreg("*", path)
        vim.api.nvim_echo({
            { " 󰾕 path_picker.lua ", "DiagnosticVirtualTextInfo" },
            { ": ", "@comment" },
            { "Copied: ", "@comment" },
            { path, "String" },
        }, true, {})
    end)
end

--- Replace visual selection with path (visual mode behavior).
local function replace_selection_with_path()
    -- Save the current visual selection positions
    local start_pos = vim.fn.getpos("'<")
    local end_pos = vim.fn.getpos("'>")

    pick_file(function(path)
        -- Delete the visual selection and insert the path
        vim.api.nvim_buf_set_text(
            0,
            start_pos[2] - 1,
            start_pos[3] - 1,
            end_pos[2] - 1,
            end_pos[3],
            { path }
        )
    end)
end

--- Configuration for the path_picker module.
---@param config? path_picker.config
path_picker.setup = function(config)
    if type(config) == "table" then
        path_picker.config = vim.tbl_extend("force", path_picker.config, config)
    end

    if path_picker.config.keymap then
        -- Normal mode: copy to clipboard
        vim.api.nvim_set_keymap("n", path_picker.config.keymap, "", {
            desc = "Pick file path and copy to clipboard",
            callback = copy_path_to_clipboard,
        })

        -- Visual mode: replace selection with path
        vim.api.nvim_set_keymap("x", path_picker.config.keymap, "", {
            desc = "Pick file path and replace selection",
            callback = function()
                -- Exit visual mode first to set '< and '> marks
                vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes("<Esc>", true, false, true), "nx", false)
                -- Schedule to ensure marks are set
                vim.schedule(replace_selection_with_path)
            end,
        })
    end
end

return path_picker
