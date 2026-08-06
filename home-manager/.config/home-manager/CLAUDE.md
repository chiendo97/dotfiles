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

**Flake inputs:** nixpkgs (unstable), home-manager, neovim-nightly-overlay, agenix, nixos-generators. Inputs that consume nixpkgs follow the top-level nixpkgs input to avoid duplicate evaluations.

### Directory Layout

- **home.nix** — Shared programs, packages, services, and session variables
- **modules/** — Personal and Uriel capability modules, including their agenix secrets and dependent configuration
- **packages/** — Modular package lists split by category (core, development, database, containers, cloud, security, linux, darwin). Each file is a function `{ pkgs }: [ ... ]` returning a list of packages
- **profiles/** — Host-specific overrides, such as selecting system Docker for `selfhost-pve`
- **hosts/** — Full NixOS host configurations
- **secrets/** — Age-encrypted secrets; `secrets.nix` defines which public keys can decrypt each `.age` file

### Home Manager Configurations

| Name | System | Notes |
|------|--------|-------|
| `cle` | x86_64-linux | Personal secrets + rootless Podman |
| `uriel-dev` | x86_64-linux | Uriel secrets + rootless Podman |
| `selfhost-pve` | x86_64-linux | Personal secrets + system Docker |
| `chiendo97` | aarch64-darwin | Personal secrets + Podman machine |

The NixOS configurations are `nixos-cle`, `homelab-pve`, and `selfhost-pve`. The
`homelab-pve` host also remains available as the `homelab-pve-image` package.

### Platform Handling

Platform-specific code uses `lib.optionals pkgs.stdenv.isLinux` / `isDarwin` guards. Linux-only: systemd services and the Podman socket. macOS-only: the Podman machine launchd agent.

## Key Patterns

### Adding Packages

Packages without Home Manager modules go in the appropriate `packages/*.nix` file. Programs with Home Manager modules are configured in `home.nix` under `programs.<name>`.

### Zsh Init Ordering

Zsh uses `lib.mkMerge` with `lib.mkBefore` to ensure the nix profile is sourced before everything else (particularly before fzf sets up keybindings).

### Secrets Management (agenix)

Two levels of agenix are in use:

- **Home Manager level** — `personal-secrets.nix` decrypts personal secrets, including Gemini in `api-keys.age`, using `~/.ssh/id_ed25519_agenix`. `uriel-secrets.nix` decrypts work secrets, including Minuet/vLLM settings in `uriel-api-keys.age`, using `~/.ssh/id_ed25519_uriel_dev`.
- **NixOS system level** — decrypts system secrets (WireGuard configs) using the host SSH key (`/etc/ssh/ssh_host_ed25519_key`). Configured in `hosts/nixos-cle/configuration.nix`.

Secrets that need system-level decryption must be encrypted with **both** the user key and the host key. See `secrets/secrets.nix` for which secrets include `nixos-cle` in their `publicKeys`.

```bash
# Edit a secret
cd secrets
age -d -i ~/.ssh/id_ed25519_agenix api-keys.age > api-keys.txt
# ... edit ...
age -r "$(cat ~/.ssh/id_ed25519_agenix.pub)" -o api-keys.age api-keys.txt
rm api-keys.txt
```

To add a new secret: (1) add an entry to `secrets/secrets.nix`, (2) encrypt it with age, and (3) add it to the owning personal, Uriel, or NixOS module. If the secret is used by a NixOS system service, include the host key in `publicKeys` and re-encrypt with both keys.

### NixOS Host (nixos-cle)

QEMU/KVM guest on Unraid with:

- **VirtioFS mounts** — `~/Source/selfhost` and `~/Source/media` from Unraid host (configured in VM XML + `fileSystems`)
- **zk notebook** — `/srv/selfhost/zk` from `nas-pve` NFS export `192.168.50.244:/zk`
- **WireGuard VPN** — `genbook-aws` and `urieljsc-office` tunnels, auto-start on boot via `networking.wg-quick` with agenix-decrypted configs
- **Rootless podman** — `virtualisation.podman.enable` + subuid/subgid ranges; socket activated via Home Manager systemd user unit. `DOCKER_HOST` points to the user podman socket so `docker compose` works transparently
- **nix-ld** — enabled for generic Linux binary compatibility (uv, etc.)
- **Tailscale** — mesh VPN for remote access

### Home Manager Options Reference

<https://nix-community.github.io/home-manager/options.xhtml>
