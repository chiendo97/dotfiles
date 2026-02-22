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
    };

    # Age-encrypted secrets management for NixOS / Home Manager
    agenix = {
      url = "github:ryantm/agenix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  # --- Flake Outputs ---
  # Destructure all inputs so they can be referenced below.
  outputs =
    { nixpkgs, home-manager, neovim-nightly-overlay, claude-code, agenix, ... }:
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
            ./home.nix
          ] ++ extraModules;
        };
    in
    {
      # --- Home Manager Configurations ---
      # Each key is a profile name used with: home-manager switch --flake .#<name>
      homeConfigurations = {
        # Linux (x86_64) - username: cle
        "cle" = mkHomeConfiguration { system = "x86_64-linux"; username = "cle"; };
        "cle@linux" = mkHomeConfiguration { system = "x86_64-linux"; username = "cle"; };

        # Linux (x86_64) with extra genbook-specific modules
        "genbook" = mkHomeConfiguration {
          system = "x86_64-linux";
          username = "cle";
          extraModules = [ ./profiles/genbook.nix ];
        };

        # macOS (Apple Silicon) - username: chiendo97
        "chiendo97" = mkHomeConfiguration { system = "aarch64-darwin"; username = "chiendo97"; };
        "chiendo97@darwin" = mkHomeConfiguration { system = "aarch64-darwin"; username = "chiendo97"; };
        "chiendo97@macos" = mkHomeConfiguration { system = "aarch64-darwin"; username = "chiendo97"; };
      };

      # --- NixOS System Configurations ---
      # Full system configs built with: nixos-rebuild switch --flake .#nixos-cle
      nixosConfigurations = {
        "nixos-cle" = nixpkgs.lib.nixosSystem {
          system = "x86_64-linux";
          modules = [
            ./hosts/nixos-cle/configuration.nix
          ];
        };
      };
    };
}
