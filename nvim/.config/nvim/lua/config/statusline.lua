local function dir_name()
    if vim.fn.getcwd() == "/" then
        return "ROOT"
    elseif vim.fn.getcwd() == "$HOME" then
        return "HOME"
    else
        return vim.fn.toupper(vim.fn.fnamemodify(vim.fn.getcwd(), ":t"))
    end
end

local file_name = "%{expand('%:~:.')!=#''?expand('%:~:.'):'[No Name]'}"

local modified = "%<%m%r%h%w"

local file_type = "%y"

local line_col_no = "%l:%c"

local pct_thru_file = "%4p%%"

vim.o.statusline = table.concat({
    dir_name(),
    " | ",
    file_name,
    modified,
    "%=", -- right_align
    file_type,
    " | ",
    line_col_no,
    pct_thru_file,
})
