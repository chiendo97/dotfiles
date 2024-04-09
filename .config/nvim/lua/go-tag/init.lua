local M = {}

local handle_job_data = function(data)
    if not data then
        return nil
    end
    -- Because the nvim.stdout's data will have an extra empty line
    -- at end on some OS (e.g. maxOS), we should remove it.
    if data[#data] == "" then
        table.remove(data, #data)
    end

    if #data < 1 then
        return nil
    end

    return data
end

local make_cmds = function(cmd_tag, cmd_option, tags, options)
    local cmds = {}
    if #tags == 0 then
        table.insert(tags, "json")
        table.insert(options, "json=omitempty")
    end

    table.insert(cmds, cmd_tag)
    table.insert(cmds, table.concat(tags, ","))

    table.insert(cmds, cmd_option)
    table.insert(cmds, table.concat(options, ","))

    return cmds
end

local get_current_filename = function()
    local fname = vim.fn.expand("%")
    return fname
end

local modify = function(start_line, end_line, byte_offset, args)
    local fname = get_current_filename()

    local cmds = { "gomodifytags", "-format", "json", "-file", fname, "-override", "-sort" }

    if byte_offset then
        table.insert(cmds, "-offset")
        table.insert(cmds, byte_offset)
    else
        table.insert(cmds, "-line")
        table.insert(cmds, start_line .. "," .. end_line)
    end

    for _, arg in ipairs(args) do
        table.insert(cmds, arg)
    end

    print(vim.inspect(table.concat(cmds, " ")))
    vim.fn.jobstart(cmds, {
        on_stderr = function(_, data, _)
            data = handle_job_data(data)
            if not data then
                return
            end
            print("ERROR", vim.inspect(data))
        end,
        on_stdout = function(_, data, _)
            data = handle_job_data(data)
            if not data then
                return
            end
            local tagged = vim.fn.json_decode(data)
            if tagged.errors ~= nil or tagged.lines == nil or tagged["start"] == nil or tagged["start"] == 0 then
                print("ERROR" .. vim.inspect(tagged))
            end
            vim.api.nvim_buf_set_lines(0, tagged["start"] - 1, tagged["start"] - 1 + #tagged.lines, false, tagged.lines)
            print("SUCCESS")
        end,
    })
end

local get_current_byte_offset = function()
    local fn = vim.fn
    local byte_offset = fn.line2byte(fn.line(".")) + fn.col(".") - 1
    return byte_offset
end

local split = function(s, delimiter)
    local result = {}
    for match in (s .. delimiter):gmatch("(.-)" .. delimiter) do
        table.insert(result, match)
    end
    return unpack(result)
end

local get_tags_options = function(args)
    local tags = {}
    local options = {}

    for _, arg in ipairs(args) do
        local tag, option = split(arg, "=")

        table.insert(tags, tag)
        if option then
            table.insert(options, tag .. "=" .. option)
        end
    end

    return tags, options
end

M.debug = function(start_line, end_line, count, args)
    dump(start_line)
    dump(end_line)
    dump(count)
    dump(args)
    local tags, options = get_tags_options(args)
    dump("tags", tags)
    dump("options", options)
end

M.add = function(start_line, end_line, count, args)
    local tags, options = get_tags_options(args)
    local cmds = make_cmds("-add-tags", "-add-options", tags, options)

    if count < 0 then
        modify(nil, nil, get_current_byte_offset(), cmds)
    else
        modify(start_line, end_line, nil, cmds)
    end
end

M.rm = function(start_line, end_line, count, args)
    local tags, options = get_tags_options(args)
    local cmds = make_cmds("-remove-tags", "-remove-options", tags, options)

    if count < 0 then
        modify(nil, nil, get_current_byte_offset(), cmds)
    else
        modify(start_line, end_line, nil, cmds)
    end
end

M.clear = function()
    modify(nil, nil, get_current_byte_offset(), { "-clear-tags" })
end

vim.cmd([[
    command! -nargs=* -range GoDebug    call luaeval("require('go-tag').debug(_A.start_line, _A.end_line, _A.count, _A.args)",{'start_line':<line1>, 'end_line':<line2>, 'count':<count>, 'args':[<f-args>]})
    command! -nargs=* -range GoAddTag   call luaeval("require('go-tag').add(_A.start_line, _A.end_line, _A.count, _A.args)",{'start_line':<line1>, 'end_line':<line2>, 'count':<count>, 'args':[<f-args>]})
    command! -nargs=* -range GoRmTag    call luaeval("require('go-tag').rm(_A.start_line, _A.end_line, _A.count, _A.args)",{'start_line':<line1>, 'end_line':<line2>, 'count':<count>, 'args':[<f-args>]})
    command!                 GoClearTag call luaeval("require('go-tag').clear()")
]])

vim.api.nvim_set_keymap("n", "<leader>i", "<cmd>%!goimports %<cr>", {})

return M
