# tmux-buffer Upgrade Design

## Goal

Upgrade the Home Manager `tmux-buffer` plugin pin to upstream commit
`da48632a66ae1200d16cd28a32ec8d6d294a0dbc`.

## Scope

- Change only the plugin revision and its fixed-output Nix hash in `home.nix`.
- Preserve the existing owner, repository, plugin name, version, runtime path,
  and tmux configuration.
- Do not stage or modify generated Codex runtime files.

## Verification

- Run `git diff --check`.
- Run `home-manager build --flake .` to confirm the new source hash and the
  complete active Home Manager configuration build successfully.
