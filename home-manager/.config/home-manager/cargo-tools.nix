# Cargo tool management module
# Declares Rust CLI tools installed via `cargo binstall` (pre-built binaries)
# or `cargo install` (compiled from source) as fallback.
#
# Usage:
#   cargoTools.tools = [
#     { crate = "xleak"; }
#     { crate = "some-tool"; features = "feat1,feat2"; }
#   ];
#
# Tools are installed once during `home-manager switch` if not already present.
# Upgrade all with: cargo install-update -a (or reinstall individually)
{ config, lib, pkgs, ... }:
let
  cargoInstallScript = lib.concatMapStringsSep "\n" (tool:
    let
      featuresFlag = if tool.features != "" then
        " --features ${tool.features}"
      else
        "";
      # Use cargo-binstall if available (fast, pre-built), fall back to cargo install
      installCmd = ''
        if ${pkgs.rustup}/bin/cargo install --list 2>/dev/null | grep -q "^${tool.crate} "; then
          echo "cargo: ${tool.crate} already installed"
        else
          echo "cargo: installing ${tool.crate}..."
          if command -v cargo-binstall &>/dev/null; then
            cargo-binstall -y "${tool.crate}"${featuresFlag} || \
              ${pkgs.rustup}/bin/cargo install "${tool.crate}"${featuresFlag} || \
              echo "Warning: Failed to install ${tool.crate}"
          else
            ${pkgs.rustup}/bin/cargo install "${tool.crate}"${featuresFlag} || \
              echo "Warning: Failed to install ${tool.crate}"
          fi
        fi
      '';
    in installCmd
  ) config.cargoTools.tools;
in {
  options.cargoTools.tools = lib.mkOption {
    type = lib.types.listOf (lib.types.submodule {
      options = {
        crate = lib.mkOption {
          type = lib.types.str;
          description = "Crate name on crates.io";
          example = "xleak";
        };
        features = lib.mkOption {
          type = lib.types.str;
          default = "";
          description = "Comma-separated feature flags";
        };
      };
    });
    default = [ ];
    description = "Rust CLI tools to install via cargo binstall/install.";
  };

  config = lib.mkIf (config.cargoTools.tools != [ ]) {
    home.activation.installCargoTools =
      lib.hm.dag.entryAfter [ "writeBoundary" ] ''
        export PATH="$HOME/.cargo/bin:$PATH"
        ${cargoInstallScript}
      '';
  };
}
