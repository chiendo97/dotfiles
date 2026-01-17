# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a personal Neovim configuration using Lua, structured as a modern modular setup with lazy.nvim plugin management. The configuration follows a clear separation of concerns with organized directories for different aspects of the editor setup.

## Architecture

### Core Structure
- `init.lua` - Main entry point, loads all configuration modules in order
- `lua/config/` - Core configuration modules (options, keymaps, autocmds, etc.)
- `lua/plugins/` - Individual plugin configurations (lazy.nvim plugin specs)
- `lsp/` - Language Server Protocol configurations for different languages
- `after/ftplugin/` - File type specific configurations

### Plugin Management
- Uses lazy.nvim for plugin management with lazy loading
- Each plugin has its own file in `lua/plugins/`
- Plugin configs return lazy.nvim specs with keys, config, and dependencies
- Development path set to `~/Source/demo` for local plugin development

### LSP Architecture
- Modern LSP setup using `vim.lsp.config()` and `vim.lsp.enable()`
- Individual server configurations in `lsp/` directory
- Global LSP configuration in `lua/config/lsp.lua`
- Supports multiple languages: Go, Lua, TypeScript, Python, Rust, Zig, Swift, etc.
- Uses blink.cmp for completion capabilities when available

## Key Conventions

### File Organization
- One plugin per file in `lua/plugins/`
- LSP server configs return a table with `cmd`, `filetypes`, `root_markers`, and `settings`
- Filetype-specific configs go in `after/ftplugin/`

### Plugin Configuration Pattern
```lua
return {
    {
        "plugin/name",
        event = "VeryLazy", -- or other lazy loading events
        keys = { -- keymaps defined here
            { "<leader>key", function() ... end, desc = "Description" },
        },
        config = function()
            -- plugin setup
        end,
    },
}
```

### LSP Configuration Pattern
```lua
return {
    cmd = { "language-server-command" },
    filetypes = { "filetype1", "filetype2" },
    root_markers = { "project-file", ".git" },
    settings = {
        -- server-specific settings
    },
}
```

## Key Features

### Fuzzy Finding (snacks.nvim picker)
- `<leader>g` - files
- `<leader>r` - live grep (visual mode: grep selection)
- `<leader>R` - grep word under cursor
- `<leader>j` - recent files with frecency
- `<leader>h` - help tags
- `<leader>m` - keymaps
- `<leader>n` - resume last search
- `<leader>b` - snacks builtins
- `<leader>s` - spell suggestions
- `<leader>i` - command history

### LSP Keymaps (buffer-local)
- `gD` - go to declaration
- `gd` - go to definition
- `gr` - go to references
- `gi` - go to implementation
- `gy` - go to type definition
- `K` - hover info
- `<leader>e` - rename symbol
- `<leader>a` - code actions
- `<leader>q` - diagnostics to quickfix
- `<leader>Q` - toggle diagnostics

### Editor Settings
- 4-space indentation, tabs converted to spaces
- No swap/backup files
- Treesitter folding enabled
- Global statusline and tabline
- Rounded borders for floating windows

## Development Commands

### Testing Configuration
```bash
# Test configuration by opening a file
nvim test.lua

# Check for errors in configuration
nvim --headless -c "checkhealth" -c "qa"
```

### Plugin Management
```bash
# Update plugins
nvim -c "Lazy update"

# Check plugin status
nvim -c "Lazy"
```

### LSP Debugging
```bash
# Check LSP status
nvim -c "LspInfo"

# Check available language servers
nvim -c "checkhealth lsp"
```

### Additional Keymaps
- `<bs>` - switch to most recent file
- `<Alt-j/k>` - move lines up/down (works in normal, insert, visual modes)
- `H`/`L` - jump to first non-blank/end of line
- `<C-c>` - clear search highlight and close quickfix window
- `*` - highlight current word (visual: search selected text)
- Tab navigation: `gt` (new), `gn`/`gp` (next/prev), `g1`-`g9` (go to tab)
- Line movement: `j`/`k` work with wrapped lines
- Clipboard: `y` yanks to system clipboard, `yy` yanks line
- Path copying: `<leader>yp` (relative), `<leader>yP` (absolute)
- Terminal: `<esc>` to exit terminal mode
- Window resize: `=/-` (vertical), `+/_` (horizontal)
- Lua execution: `<leader>x` (line/selection), `<leader><space>x` (source file)
- `yc` - duplicate line and comment original
- Search & replace: `<leader>e` - replace word under cursor
- Sort: `<leader>s` (visual selection)

## Important Notes

- Configuration disables nested nvim instances (exits with status 2)
- Many built-in providers and plugins are disabled for performance
- Uses ripgrep for search when available
- Clipboard operations use system clipboard (`"*` register)
- Leader key is space (`<space>`)
- Uses treesitter for syntax highlighting and folding
- Snacks.nvim provides file explorer (`<leader>c`), picker, and notification system (`<leader>t`)
- Global debug functions: `dd()` for inspection, `bt()` for backtrace
- LSP servers automatically disable formatting for specific servers (gopls, lua_ls, basedpyright, ruff)
- Some servers have specific capability adjustments (basedpyright semantic tokens disabled, ruff hover disabled)
