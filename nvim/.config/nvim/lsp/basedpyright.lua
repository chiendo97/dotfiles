local function get_python_path()
    -- Use activated virtualenv.
    if vim.env.VIRTUAL_ENV then
        return vim.fn.expand(vim.env.VIRTUAL_ENV .. "/bin/python")
    end

    local venv_python = vim.fn.expand(vim.loop.cwd() .. "/.venv/bin/python")
    if vim.loop.fs_stat(venv_python) then
        return venv_python
    end

    -- Fallback to system Python.
    return vim.fn.exepath("python3") or vim.fn.exepath("python") or "python"
end

return {
    cmd = { "basedpyright-langserver", "--stdio" },
    filetypes = { "python" },
    root_markers = {
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "requirements.txt",
        "Pipfile",
        "pyrightconfig.json",
        ".git",
    },
    settings = {
        basedpyright = {
            analysis = {
                autoSearchPaths = true,
                diagnosticMode = "openFilesOnly",
                useLibraryCodeForTypes = true,
                typeCheckingMode = "all",
                diagnosticSeverityOverrides = {
                    reportAny = false,
                    reportImplicitOverride = false,
                    reportMissingParameterType = false,
                    reportMissingTypeArgument = false,
                    reportMissingTypeStubs = false,
                    reportUnannotatedClassAttribute = false,
                    reportUnknownArgumentType = false,
                    reportUnknownLambdaType = false,
                    reportUnknownMemberType = false,
                    reportUnknownParameterType = false,
                    reportUnknownVariableType = false,
                    reportUnusedCallResult = false,
                },
            },
        },
        python = {},
    },
    before_init = function(_, config)
        local python_path = get_python_path()
        config.settings.python.pythonPath = python_path
        vim.notify(string.format("python path: %s", python_path))
    end,
}
