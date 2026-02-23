# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Home Manager + NixOS flake configuration managing user environment and dotfiles. Supports Linux (x86_64) and macOS (aarch64-darwin) via the `nixos-unstable` channel.

## Common Commands

```bash
# Apply configuration (auto-detects $USER)
home-manager switch --flake .

# Build without activating (for testing)
home-manager build --flake .

# Dry-run to preview changes
home-manager switch --flake . --dry-run

# Validate flake
nix flake check

# Update all flake inputs
nix flake update

# Rebuild NixOS system (for nixos-cle host)
sudo nixos-rebuild switch --flake .#nixos-cle
```

## Architecture

### Flake Structure

`flake.nix` defines a `mkHomeConfiguration` helper that builds Home Manager configs from three parameters: `system`, `username`, and optional `extraModules` for host-specific overrides. It also defines NixOS system configurations under `nixosConfigurations`.

**Flake inputs:** nixpkgs (unstable), home-manager, neovim-nightly-overlay, claude-code-nix, agenix. All inputs follow nixpkgs to avoid duplicate evaluations.

### Directory Layout

- **home.nix** — Main module: agenix secrets, program configs (tmux, zsh, ssh, neovim), systemd services, session variables
- **packages/** — Modular package lists split by category (core, development, database, containers, cloud, ai, security, linux, darwin). Each file is a function `{ pkgs }: [ ... ]` returning a list of packages
- **profiles/** — Host-specific modules loaded via `extraModules` (e.g., `genbook.nix` adds rclone mount services)
- **hosts/nixos-cle/** — Full NixOS system configuration (`configuration.nix` + `hardware-configuration.nix`)
- **secrets/** — Age-encrypted secrets; `secrets.nix` defines which public keys can decrypt each `.age` file

### Available Configurations

| Name | System | Notes |
|------|--------|-------|
| `cle` / `cle@linux` | x86_64-linux | Default Linux config |
| `genbook` | x86_64-linux | Linux + rclone mount services |
| `chiendo97` / `chiendo97@darwin` / `chiendo97@macos` | aarch64-darwin | macOS config |

### Platform Handling

Platform-specific code uses `lib.optionals pkgs.stdenv.isLinux` / `isDarwin` guards. Linux-only: systemd services, podman socket, `DOCKER_HOST`. macOS-only: launchd agents (auto-update cron).

## Key Patterns

### Adding Packages

Packages without Home Manager modules go in the appropriate `packages/*.nix` file. Programs with Home Manager modules are configured in `home.nix` under `programs.<name>`.

### Zsh Init Ordering

Zsh uses `lib.mkMerge` with `lib.mkBefore` to ensure the nix profile is sourced before everything else (particularly before fzf sets up keybindings).

### Secrets Management (agenix)

Identity key: `~/.ssh/id_ed25519_agenix`. Secrets decrypt to paths defined in `age.secrets` (e.g., `~/.secrets/api-keys`, `~/.ssh/*`). SSH keys use a `builtins.listToAttrs + map` pattern for bulk declaration.

```bash
# Edit a secret
cd secrets
age -d -i ~/.ssh/id_ed25519_agenix api-keys.age > api-keys.txt
# ... edit ...
age -r "$(cat ~/.ssh/id_ed25519_agenix.pub)" -o api-keys.age api-keys.txt
rm api-keys.txt
```

To add a new secret: (1) add entry to `secrets/secrets.nix`, (2) encrypt with age, (3) add to `age.secrets` in `home.nix`.

### Home Manager Options Reference

<https://nix-community.github.io/home-manager/options.xhtml>
