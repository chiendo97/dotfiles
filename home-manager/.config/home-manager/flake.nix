{
  description = "Home Manager configuration";

  # --- Flake Inputs ---
  # External dependencies fetched and pinned via flake.lock.
  # "follows" ensures inputs share the same nixpkgs to avoid duplicate evaluations.
  inputs = {
    # Main package repository — tracking the rolling unstable channel
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

    # Declarative user-environment manager (dotfiles, packages, services)
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    # Nightly Neovim builds overlay
    neovim-nightly-overlay = {
      url = "github:nix-community/neovim-nightly-overlay";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    # Claude Code CLI package (third-party flake)
    claude-code = {
      url = "github:sadjow/claude-code-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    # Age-encrypted secrets management for NixOS / Home Manager
    agenix = {
      url = "github:ryantm/agenix";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    # Build NixOS images in alternative formats (Proxmox VMA, LXC, qcow2, etc.)
    nixos-generators = {
      url = "github:nix-community/nixos-generators";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  # --- Flake Outputs ---
  # Destructure all inputs so they can be referenced below.
  outputs =
    { nixpkgs, home-manager, neovim-nightly-overlay, claude-code, agenix, nixos-generators, ... }:
    let
      # Helper function to build a Home Manager configuration.
      # Arguments:
      #   system       — architecture string, e.g. "x86_64-linux" or "aarch64-darwin"
      #   username     — the user account name
      #   extraModules — optional list of additional Nix modules to include
      mkHomeConfiguration = { system, username, extraModules ? [] }:
        let
          # Instantiate nixpkgs for the target system with unfree packages
          # and overlays for third-party packages (claude-code, neovim-nightly).
          pkgs = import nixpkgs {
            inherit system;
            config.allowUnfree = true;
            overlays = [
              claude-code.overlays.default
              neovim-nightly-overlay.overlays.default
            ];
          };

          # Derive the home directory path based on the OS
          homeDirectory = if pkgs.stdenv.isDarwin then "/Users/${username}" else "/home/${username}";
        in
        home-manager.lib.homeManagerConfiguration {
          inherit pkgs;

          # Extra arguments passed to every module (accessible as function args in home.nix, etc.)
          extraSpecialArgs = {
            inherit homeDirectory username;
          };

          # Modules composing this configuration:
          #   1. agenix — enables age.secrets options in Home Manager
          #   2. home.nix — main user configuration
          #   3. any extra per-host modules
          modules = [
            agenix.homeManagerModules.default
            ./uv-tools.nix
            ./cargo-tools.nix
            ./home.nix
          ] ++ extraModules;
        };
    in
    {
      # --- Home Manager Configurations ---
      # Each key is a profile name used with: home-manager switch --flake .#<name>
      homeConfigurations = {
        # Linux (x86_64) - username: cle
        "cle" = mkHomeConfiguration {
          system = "x86_64-linux";
          username = "cle";
          extraModules = [
            ./modules/personal-secrets.nix
            ./modules/uriel-secrets.nix
          ];
        };

        # Linux (x86_64) with extra genbook-specific modules
        "genbook" = mkHomeConfiguration {
          system = "x86_64-linux";
          username = "cle";
          extraModules = [
            ./modules/personal-secrets.nix
            ./modules/uriel-secrets.nix
            ./profiles/genbook.nix
          ];
        };

        # Linux (x86_64) - uriel dev machine (work secrets only, no personal secrets)
        "uriel-dev" = mkHomeConfiguration {
          system = "x86_64-linux";
          username = "cle";
          extraModules = [ ./modules/uriel-secrets.nix ];
        };

        # Selfhost Proxmox VM — personal shell config, but use the system Docker
        # daemon instead of the default rootless Podman socket.
        "selfhost-pve" = mkHomeConfiguration {
          system = "x86_64-linux";
          username = "cle";
          extraModules = [
            ./modules/personal-secrets.nix
            ./profiles/selfhost-pve.nix
          ];
        };

        # macOS (Apple Silicon) - username: chiendo97
        "chiendo97" = mkHomeConfiguration {
          system = "aarch64-darwin";
          username = "chiendo97";
          extraModules = [ ./modules/personal-secrets.nix ];
        };
      };

      # --- NixOS System Configurations ---
      # Full system configs built with: nixos-rebuild switch --flake .#nixos-cle
      nixosConfigurations = {
        "nixos-cle" = nixpkgs.lib.nixosSystem {
          system = "x86_64-linux";
          modules = [
            agenix.nixosModules.default
            ./hosts/nixos-cle/configuration.nix
          ];
        };

        # Proxmox VM — managed with `nixos-rebuild switch --flake .#homelab-pve`
        # after the initial image has been imported.
        "homelab-pve" = nixpkgs.lib.nixosSystem {
          system = "x86_64-linux";
          modules = [
            agenix.nixosModules.default
            ./hosts/homelab-pve/hardware-configuration.nix
            ./hosts/homelab-pve/configuration.nix
          ];
        };

        # Selfhost Proxmox VM. Replaces the old Debian Docker VM.
        "selfhost-pve" = nixpkgs.lib.nixosSystem {
          system = "x86_64-linux";
          modules = [
            agenix.nixosModules.default
            ./hosts/selfhost-pve/configuration.nix
          ];
        };
      };

      # --- Build artifacts ---
      # Proxmox VMA image: `nix build .#homelab-pve-image`
      # Output: result/vzdump-qemu-*.vma.zst — restore via Proxmox UI or `qmrestore`.
      packages.x86_64-linux = {
        homelab-pve-image = nixos-generators.nixosGenerate {
          system = "x86_64-linux";
          format = "proxmox";
          modules = [
            ./hosts/homelab-pve/configuration.nix
            {
              proxmox.qemuConf = {
                name = "homelab-pve";
                cores = 4;
                memory = 8192;
              };
            }
          ];
        };

        selfhost-pve-image = nixos-generators.nixosGenerate {
          system = "x86_64-linux";
          format = "proxmox";
          modules = [
            agenix.nixosModules.default
            ./hosts/selfhost-pve/configuration.nix
            {
              proxmox.qemuConf = {
                name = "selfhost-pve";
                cores = 8;
                memory = 12288;
              };
            }
          ];
        };
      };
    };
}
