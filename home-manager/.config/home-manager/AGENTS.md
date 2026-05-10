# AGENTS.md

Guidance for coding agents working in this Home Manager + NixOS flake configuration.

## Commands

- Build the active Home Manager config: `home-manager build --flake .`
- Apply the current host profile: `home-manager switch --flake .#selfhost-pve`
- Validate the selfhost profile derivation: `nix eval .#homeConfigurations.selfhost-pve.activationPackage.drvPath`
- Validate formatting hazards before committing: `git diff --check`

## Editing Rules

- Keep changes scoped to this Home Manager config unless the task explicitly targets the wider dotfiles repo.
- Do not stage or clean generated Codex runtime files under `codex/.codex/`.
- Prefer package additions in `packages/*.nix`; use `home.nix` for Home Manager modules, activation hooks, session variables, and program configuration.
- Preserve platform guards such as `pkgs.stdenv.isLinux` and `pkgs.stdenv.isDarwin`.
- Do not decrypt or rewrite age secrets unless explicitly asked.

## Local Patterns

- `uvTools.tools` manages Python CLI tools through uv during Home Manager activation.
- `cargoTools.tools` manages Rust CLI tools through cargo-binstall during Home Manager activation.
- The global user `python` and `python3` shims are intentionally uv-managed via `home.activation.installUvPython`.
- Host-specific Home Manager modules live under `profiles/`; full NixOS host configs live under `hosts/`.
