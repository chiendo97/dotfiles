{
  description = "Home Manager configuration";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    neovim-nightly-overlay = {
      url = "github:nix-community/neovim-nightly-overlay";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    claude-code = {
      url = "github:sadjow/claude-code-nix";
    };
    agenix = {
      url = "github:ryantm/agenix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    { nixpkgs, home-manager, neovim-nightly-overlay, claude-code, agenix, ... }:
    let
      mkHomeConfiguration = { system, username }:
        let
          pkgs = import nixpkgs {
            inherit system;
            config.allowUnfree = true;
            overlays = [ claude-code.overlays.default ];
          };
          homeDirectory = if pkgs.stdenv.isDarwin then "/Users/${username}" else "/home/${username}";
        in
        home-manager.lib.homeManagerConfiguration {
          inherit pkgs;
          extraSpecialArgs = {
            inherit neovim-nightly-overlay homeDirectory username;
          };
          modules = [
            agenix.homeManagerModules.default
            ./home.nix
          ];
        };
    in
    {
      homeConfigurations = {
        # Linux (x86_64) - username: cle
        "cle" = mkHomeConfiguration { system = "x86_64-linux"; username = "cle"; };
        "cle@linux" = mkHomeConfiguration { system = "x86_64-linux"; username = "cle"; };

        # macOS (Apple Silicon) - username: chiendo97
        "chiendo97" = mkHomeConfiguration { system = "aarch64-darwin"; username = "chiendo97"; };
        "chiendo97@darwin" = mkHomeConfiguration { system = "aarch64-darwin"; username = "chiendo97"; };
        "chiendo97@macos" = mkHomeConfiguration { system = "aarch64-darwin"; username = "chiendo97"; };
      };
    };
}
