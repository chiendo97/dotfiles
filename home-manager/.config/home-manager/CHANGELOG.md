# Changelog

All notable changes to this Home Manager configuration are tracked here.

## Unreleased

### Added

- Install a uv-managed global Python 3 during Home Manager activation.
- Make `python`, `python3`, and the current versioned Python executable resolve from uv's managed Python directory when available.
- Add a guard that refuses to replace an existing non-uv `~/.local/bin/python3`.
