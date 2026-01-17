# Dotfiles

Personal dotfiles for a complete development environment. Uses **Nix Home Manager** for declarative package management and **GNU Stow** for config symlinks.

## Structure

```
dotfiles/
├── home-manager/    # Nix flakes + Home Manager (packages, shell, SSH, secrets)
├── nvim/            # Neovim configuration (Lua, lazy.nvim, LSP)
├── alacritty/       # Terminal emulator (Gruvbox theme)
├── zellij/          # Terminal multiplexer alternative
└── Makefile         # Stow commands
```

## Bootstrap (New Machine)

### Prerequisites

- `id_ed25519_agenix` key (for decrypting secrets)

### 1. Install Nix

```bash
sh <(curl -L https://nixos.org/nix/install) --daemon

# Restart shell or source nix
. ~/.nix-profile/etc/profile.d/nix.sh
```

### 2. Enable Flakes

```bash
mkdir -p ~/.config/nix
echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf
```

### 3. Copy Agenix Key

```bash
mkdir -p ~/.ssh
cp /path/to/id_ed25519_agenix ~/.ssh/
cp /path/to/id_ed25519_agenix.pub ~/.ssh/
chmod 600 ~/.ssh/id_ed25519_agenix
chmod 644 ~/.ssh/id_ed25519_agenix.pub
```

### 4. Clone Dotfiles

```bash
# Use HTTPS (SSH keys not yet available)
git clone https://github.com/chiendo97/dotfiles ~/Source/dotfiles
```

### 5. Apply Home Manager

```bash
# Auto-detects config based on $USER (works on both Linux and macOS)
nix run home-manager -- switch --flake ~/Source/dotfiles/home-manager/.config/home-manager
```

This installs all packages and configures:
- Shell (zsh, fzf, zoxide)
- SSH keys (decrypted via agenix)
- CLI tools (neovim, tmux, ripgrep, fd, etc.)

### 6. Stow Config Packages

```bash
cd ~/Source/dotfiles
make stow
```

### 7. Switch Git Remote to SSH

```bash
cd ~/Source/dotfiles
git remote set-url origin git@github.com:chiendo97/dotfiles.git
```

## Daily Usage

### Home Manager

```bash
# Apply config changes (auto-detects by $USER)
home-manager switch --flake ~/.config/home-manager

# Update all packages
cd ~/.config/home-manager && nix flake update
```

### Stow

```bash
make stow      # Symlink all packages
make unstow    # Remove all symlinks
make restow    # Re-symlink all (after changes)
make nvim      # Stow individual package
```

### Neovim

```bash
nvim -c "Lazy update"    # Update plugins
```

### Tmux

- Prefix: `C-Space`
- Reload: `prefix + r`
- Install plugins: `prefix + I`

## Secrets Management

SSH keys and API tokens are encrypted with [agenix](https://github.com/ryantm/agenix) using `id_ed25519_agenix`.

```bash
# Edit a secret
cd ~/.config/home-manager/secrets
age -d -i ~/.ssh/id_ed25519_agenix api-keys.age > api-keys.txt
# ... edit ...
age -r "$(cat ~/.ssh/id_ed25519_agenix.pub)" -o api-keys.age api-keys.txt
rm api-keys.txt
```

## Migrating Agenix Key

The `id_ed25519_agenix` key decrypts all secrets. To set up a new machine:

1. **Secure copy**: USB drive or password manager
2. **Multi-key setup**: Add new machine's key to `secrets/secrets.nix` and re-encrypt

## Notes

- Platforms: Linux (x86_64), macOS (Apple Silicon & Intel)
- Font: Nerd Font (Liga SFMono or Hack Nerd Font)
- Theme: Gruvbox (consistent across Alacritty, Neovim, Tmux)
