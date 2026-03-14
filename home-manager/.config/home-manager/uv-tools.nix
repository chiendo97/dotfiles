# UV tool management module
# Declares Python CLI tools installed via `uv tool install`.
# Each tool gets its own isolated venv; binaries are symlinked to ~/.local/bin/.
#
# Usage:
#   uvTools.tools = [
#     { package = "mkdocs"; }
#     { package = "some-tool"; extras = "ssh,cloud"; }
#     { package = "some-tool"; inject = [ "extra-dep" ]; }
#   ];
#
# Tools are installed once during `home-manager switch` if not already present.
# Upgrade all with: uv tool upgrade --all
{ config, lib, pkgs, ... }:
let
  uvToolInstallScript = lib.concatMapStringsSep "\n" (tool:
    let
      spec = if tool.extras != "" then
        "${tool.package}[${tool.extras}]"
      else
        tool.package;
      installCmd = ''
        if ${pkgs.uv}/bin/uv tool list 2>/dev/null | grep -q "^${tool.package} "; then
          echo "uv tool: ${tool.package} already installed"
        else
          echo "uv tool: installing ${tool.package}..."
          ${pkgs.uv}/bin/uv tool install "${spec}" || echo "Warning: Failed to install ${tool.package}"
        fi
      '';
      injectCmds = lib.concatMapStringsSep "\n" (dep: ''
        ${pkgs.uv}/bin/uv tool inject "${tool.package}" "${dep}" 2>/dev/null || true
      '') tool.inject;
    in installCmd + injectCmds
  ) config.uvTools.tools;
in {
  options.uvTools.tools = lib.mkOption {
    type = lib.types.listOf (lib.types.submodule {
      options = {
        package = lib.mkOption {
          type = lib.types.str;
          description = "PyPI package name";
          example = "mkdocs";
        };
        extras = lib.mkOption {
          type = lib.types.str;
          default = "";
          description = "Comma-separated extras (e.g., 'ssh,cloud')";
        };
        inject = lib.mkOption {
          type = lib.types.listOf lib.types.str;
          default = [ ];
          description = "Packages to inject into the tool's isolated venv";
        };
      };
    });
    default = [ ];
    description = "Python CLI tools to install via uv tool install.";
  };

  config = lib.mkIf (config.uvTools.tools != [ ]) {
    home.activation.installUvTools =
      lib.hm.dag.entryAfter [ "writeBoundary" ] ''
        ${uvToolInstallScript}
      '';
  };
}
