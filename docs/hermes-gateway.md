# Hermes Gateway dotfiles

The `hermes/` GNU Stow package contains public, reproducible customizations for the `hermes` gateway account:

- `.bash_profile`: enters Home Manager Zsh for interactive login shells while preserving non-interactive SSH/SCP/SFTP behavior.
- `.config/systemd/user/hermes-gateway.service.d/path.conf`: puts Home Manager packages first in the gateway service `PATH`.
- `.hermes/skills/`: selected Claude/Codex skills adapted to Hermes paths and conventions.

The ARM64 Home Manager profile is `home-manager/.config/home-manager/profiles/hermes-gateway.nix` and is exposed as `homeConfigurations.hermes` in the flake. Git is supplied by Home Manager so settings such as `merge.conflictStyle=zdiff3` work during Neovim `vim.pack` checkouts.

Deploy with:

```sh
make hermes
home-manager switch --flake ~/.config/home-manager#hermes
systemctl --user daemon-reload
systemctl --user restart hermes-gateway.service
```

## Intentionally not tracked

Do not add Hermes runtime state or credentials to this repository, including:

- `~/.hermes/.env`
- `~/.hermes/config.yaml`
- authentication/token files
- sessions, logs, caches, cron state, memories, and user profile data
- cloned Hermes Agent source or its virtual environment

Keep secrets in the gateway systemd environment or another host-local secret store.
