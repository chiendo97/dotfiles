# Hermes Gateway dotfiles

The `hermes/` GNU Stow package contains public, reproducible customizations for the `hermes` gateway account:

- `.bash_profile`: enters Zsh from the user Nix profile when available while preserving non-interactive SSH/SCP/SFTP behavior.
- `.config/systemd/user/hermes-gateway.service.d/path.conf`: puts user-profile packages first in the gateway service `PATH`.
- `.hermes/skills/`: selected Claude/Codex skills adapted to Hermes paths and conventions.
- `.hermes/config-templates/rocky-personality.yaml`: secret-free Rocky personality fragment for restoring `agent.personalities.rocky` and `agent.system_prompt`.

The Rocky file is a template, not the live config. Merge its `agent` keys into `~/.hermes/config.yaml`, then restart the gateway and create a fresh session with `/new`. Keeping the live `config.yaml` outside Git prevents credentials and host-specific settings from leaking.

The Hermes account is not managed by this repository's Home Manager flake. Install and maintain its user-profile packages on the host; this repository only deploys the public Stow configuration described above.

Deploy with:

```sh
make hermes
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
