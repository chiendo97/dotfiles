{
  description = "Home Manager configuration of cle";

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
      mkHomeConfiguration = system:
        let
          pkgs = import nixpkgs {
            inherit system;
            config.allowUnfree = true;
            overlays = [ claude-code.overlays.default ];
          };
          homeDirectory = if pkgs.stdenv.isDarwin then "/Users/cle" else "/home/cle";
        in
        home-manager.lib.homeManagerConfiguration {
          inherit pkgs;
          extraSpecialArgs = {
            inherit neovim-nightly-overlay homeDirectory;
          };
          modules = [
            agenix.homeManagerModules.default
            ./home.nix
          ];
        };
    in
    {
      homeConfigurations = {
        # Linux (x86_64)
        "cle" = mkHomeConfiguration "x86_64-linux";
        "cle@linux" = mkHomeConfiguration "x86_64-linux";

        # macOS (Apple Silicon)
        "cle@darwin" = mkHomeConfiguration "aarch64-darwin";
        "cle@macos" = mkHomeConfiguration "aarch64-darwin";

        # macOS (Intel)
        "cle@darwin-x86" = mkHomeConfiguration "x86_64-darwin";
      };
    };
}
