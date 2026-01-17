# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Home Manager configuration repository that manages user environment and dotfiles using Nix flakes. The configuration is for user "cle" on a Linux system (x86_64-linux) and uses the `nixos-unstable` channel.

## Architecture

### Flake Structure
- **flake.nix**: Defines the flake inputs (nixpkgs, home-manager, neovim-nightly-overlay) and outputs a single home configuration named "cle"
- **home.nix**: Main configuration module containing all package installations, program configurations, and shell setup

### Key Inputs
- `nixpkgs`: Following nixos-unstable channel
- `home-manager`: Home Manager framework from nix-community
- `neovim-nightly-overlay`: Provides nightly Neovim builds

## Common Commands

### Building and Applying Configuration
```bash
# Auto-detects config based on $USER (works on both Linux and macOS)
home-manager switch --flake .

# Or explicitly specify:
# home-manager switch --flake .#cle        # Linux
# home-manager switch --flake .#chiendo97  # macOS

# Build without activating (for testing)
home-manager build --flake .

# Check what would change
home-manager switch --flake . --dry-run
```

### Available Configurations
| Name | System | Username | Home Directory |
|------|--------|----------|----------------|
| `cle` | x86_64-linux | cle | /home/cle |
| `cle@linux` | x86_64-linux | cle | /home/cle |
| `chiendo97` | aarch64-darwin | chiendo97 | /Users/chiendo97 |
| `chiendo97@darwin` | aarch64-darwin | chiendo97 | /Users/chiendo97 |
| `chiendo97@macos` | aarch64-darwin | chiendo97 | /Users/chiendo97 |

### Updating Dependencies
```bash
# Update all flake inputs
nix flake update

# Update specific input
nix flake lock --update-input nixpkgs
nix flake lock --update-input home-manager
```

### Testing and Validation
```bash
# Check flake for errors
nix flake check

# Show flake metadata
nix flake metadata

# Show flake outputs
nix flake show
```

## Configuration Structure

### Package Management
- `home.packages`: Direct package installations without Home Manager modules (e.g., claude-code, fd, ripgrep, rustup)
- `programs.<name>`: Programs configured through Home Manager modules with additional settings

### Program Configurations

**Programs with custom configuration:**
- **tmux**: Extensive customization with vi keybindings, Gruvbox theme, vim-tmux navigation integration, custom key bindings
  - Prefix: `C-Space`
  - Plugins: cpu, prefix-highlight, yank, sensible, tmux-buffer
- **zsh**: Complete shell configuration with history, aliases, session variables, lazy-loading nvm
  - Plugins: pure (prompt), zsh-autosuggestions
- **neovim**: Uses nightly build from neovim-nightly-overlay

**Programs with minimal configuration:**
- fzf, zoxide (both with Zsh integration)
- go, eza, bat

### Important Variables and Paths
- `home.stateVersion = "25.11"`: Home Manager version lock
- Session paths: `~/.local/bin`, `~/.cargo/bin`, `~/go/bin`
- Editor: nvim
- Go environment: `GO111MODULE=auto`, `GOSUMDB=off`

## Development Workflow

### Adding New Packages
Add to `home.packages` list if no Home Manager module exists, or configure under `programs.<name>` if a module is available.

### Modifying Program Configurations
Most program configurations use Home Manager's declarative options. Refer to the Home Manager manual for available options: https://nix-community.github.io/home-manager/options.xhtml

### Shell Configuration
Zsh configuration uses `lib.mkMerge` and `lib.mkBefore` for proper initialization ordering. The nix profile is sourced early in the initialization sequence.

### Secrets Management (agenix)

Secrets are encrypted with age using your SSH key and decrypted at activation.

```
secrets/
├── secrets.nix      # Defines which keys can decrypt which secrets
├── api-keys.age     # Encrypted API keys
└── api-keys.example # Template (not committed)
```

**Edit secrets:**
```bash
cd secrets
age -d -i ~/.ssh/id_ed25519_agenix api-keys.age > api-keys.txt
# Edit api-keys.txt
age -r "$(cat ~/.ssh/id_ed25519_agenix.pub)" -o api-keys.age api-keys.txt
rm api-keys.txt
```

**Add new secret:**
1. Add entry to `secrets.nix`
2. Create encrypted file: `echo "content" | age -r "$(cat ~/.ssh/id_ed25519_agenix.pub)" -o newsecret.age`
3. Add to `home.nix` under `age.secrets`
