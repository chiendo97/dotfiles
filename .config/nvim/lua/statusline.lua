local function dirname()
    if vim.fn.getcwd() == "/" then
        return "ROOT"
    elseif vim.fn.getcwd() == "$HOME" then
        return "HOME"
    else
        return vim.fn.toupper(vim.fn.fnamemodify(vim.fn.getcwd(), ":t"))
    end
end

local stl = {
    dirname(),
    " ",
    "|",
    " %{expand('%:~:.')!=#''?expand('%:~:.'):'[No Name]'} ",
    "%<%m%r%h%w",
    "%=",
    " %02v ",
    "|",
    " %l:%c",
    " %p%% ",
}

vim.o.statusline = table.concat(stl)
