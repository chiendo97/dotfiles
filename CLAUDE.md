# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Personal dotfiles repository for a complete development environment. Manages shell, terminal, editor, and system configurations across Linux/macOS.

## Structure

Uses GNU Stow with individual packages. Each package contains a `.config/` directory that gets symlinked to `~/.config/`.

```
nvim/.config/nvim/  →  ~/.config/nvim
alacritty/.config/alacritty/  →  ~/.config/alacritty
```

### Stow Packages

| Directory | Purpose | Has CLAUDE.md |
|-----------|---------|---------------|
| `nvim/` | Neovim configuration (Lua, lazy.nvim, LSP) | Yes |
| `home-manager/` | Nix flakes + Home Manager for declarative system config | Yes |
| `alacritty/` | Terminal emulator (Gruvbox theme, Liga SFMono font) | No |
| `zellij/` | Terminal multiplexer alternative (KDL config) | No |

### Root Configuration Files (not managed by stow)

| File | Purpose |
|------|---------|
| `.zshrc` | Zsh shell (Pure prompt, zoxide, fzf, lazy nvm) |
| `.tmux.conf` | Tmux (vim-tmux navigation, Gruvbox, TPM plugins) |
| `.gitconfig` | Git (delta for diffs, custom aliases, LFS) |
| `.editorconfig` | Editor indentation standards |

## Stow Commands

```bash
make stow      # Symlink all packages
make unstow    # Remove all symlinks
make restow    # Re-symlink all (after changes)
make nvim      # Stow individual package
```

## Key Integration Points

- **vim-tmux navigation**: Ctrl-hjkl seamlessly moves between Neovim splits and tmux panes
- **Gruvbox theme**: Consistent across Alacritty, Neovim, and Tmux
- **System clipboard**: Shared between terminal, Neovim, and tmux
- **Home Manager**: Declaratively manages most tool installations and configs

## Common Workflows

### Home Manager (Nix-based system management)
```bash
# Apply configuration changes
home-manager switch --flake ~/.config/home-manager#cle

# Update all packages
cd ~/.config/home-manager && nix flake update
```

### Neovim
```bash
# Update plugins
nvim -c "Lazy update"

# Health check
nvim --headless -c "checkhealth" -c "qa"
```

### Tmux
- Prefix: `C-Space`
- Reload config: `prefix + r`
- Plugins managed by TPM (install with `prefix + I`)

## Notes

- Forked from [chiendo97/dotfiles](https://github.com/chiendo97/dotfiles)
- Primary platform: Linux (x86_64), with macOS support via Homebrew
- Font requirement: Nerd Font (Liga SFMono or Hack Nerd Font)
- See subdirectory CLAUDE.md files for detailed component documentation
