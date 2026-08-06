# Changelog

All notable changes to this Home Manager configuration are tracked here.

## Unreleased

### Changed

- Limit Home Manager profiles to personal, Uriel, and selfhost capability combinations.
- Consolidate Gemini into the personal API-key bundle and Minuet/vLLM settings into the Uriel API-key bundle, and move Uriel GitLab activation into the Uriel module.
- Keep `homelab-pve` as a NixOS host and Proxmox image without a Home Manager profile.

### Added

- Install a uv-managed global Python 3 during Home Manager activation.
- Make `python`, `python3`, and the current versioned Python executable resolve from uv's managed Python directory when available.
- Add a guard that refuses to replace an existing non-uv `~/.local/bin/python3`.
