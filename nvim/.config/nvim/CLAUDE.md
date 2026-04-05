# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Personal Neovim configuration using Lua with vim.pack (Neovim's native package manager) for plugin management.

## Architecture

### Loading Order

1. `init.lua` — Entry point: loads config modules, registers PackChanged hooks for vim.pack
2. `lua/config/` — Core modules: options, keymaps, autocmds, statusline, tabline, LSP, diagnostics
3. `plugin/` — Plugin loading files, sourced automatically by Neovim in alphabetical order
   - `00-*` prefix = early load (colorscheme, snacks, mini)
   - `zz-*` prefix = late load (LSP setup, after all plugins are available)
4. `lsp/` — Per-language LSP server configurations
5. `after/ftplugin/` — Filetype-specific overrides

### Plugin Management: vim.pack (NOT lazy.nvim)

Plugins are managed via `vim.pack.add()` — **not** lazy.nvim. The lock file is `nvim-pack-lock.json`. Each plugin has its own file in `plugin/`.

Four loading patterns are used:

1. **Immediate**: `vim.pack.add({...})` then `require(...).setup()` — most plugins
2. **Deferred**: Wrapped in `vim.schedule()` — gitsigns, treesitter, which-key
3. **Filetype-triggered**: `nvim_create_autocmd("FileType", ...)` — lazydev (lua), render-markdown
4. **Command-triggered**: `nvim_create_user_command(...)` — StartupTime, JqPlayground, rarely-used tools

### Plugin Configuration Pattern

```lua
-- plugin/example.lua
vim.pack.add({ "https://github.com/author/plugin.nvim" })
require("plugin").setup({ ... })
```

### LSP Architecture

- Uses native `vim.lsp.config()` / `vim.lsp.enable()` (not nvim-lspconfig)
- Global config in `lua/config/lsp.lua`, loaded from `plugin/zz-lsp.lua`
- Per-server configs in `lsp/` return `{ cmd, filetypes, root_markers, settings }`
- Active servers list is in `lua/config/lsp.lua` — add/remove from the `lsp_servers` table
- Custom user commands: `:LspStart`, `:LspStop`, `:LspRestart`, `:LspInfo`, `:LspLog`

### Core Plugin Infrastructure

- **mini.nvim**: statusline, completion, snippets, file explorer (`<leader>c`), surround, AI text objects, cmdline, icons
- **snacks.nvim**: fuzzy picker, notifications, and UI utilities
- **conform.nvim**: formatting
- **treesitter**: syntax highlighting and folding

## Key Conventions

- One plugin per file in `plugin/`
- LSP server configs in `lsp/` return a plain table (no function wrapper)
- Filetype configs go in `after/ftplugin/`
- Leader key is `<space>`
- Nested nvim instances are blocked (exits with status 2)
- Clipboard uses `"*` register (system clipboard)

## Development Commands

```bash
# Check for config errors
nvim --headless -c "checkhealth" -c "qa"

# LSP status
:LspInfo          # alias for :checkhealth vim.lsp
:LspLog           # open LSP log file
:LspRestart       # restart all or specific LSP server
:LspRestart!      # force stop then restart
```

## Important Notes

- `<leader>e` is **search & replace** (global keymaps) but **rename symbol** (LSP buffer-local override) — the LSP keymap takes precedence when an LSP is attached
- PackChanged hook in init.lua auto-runs `:TSUpdate` when treesitter is updated
- `plugin/dev.lua` loads local development plugins from `~/Source/demo`
