# Remove Home Manager Auto-Update Agent Design

## Goal

Remove the macOS `com.home-manager.auto-update` launchd agent, update the flake
inputs manually, and activate the upgraded `chiendo97` Home Manager profile.

## Scope

- Delete only the `launchd.agents.home-manager-auto-update` declaration from
  `home.nix`.
- Keep the `com.podman.machine` launchd agent unchanged.
- Update `flake.lock` with `nix flake update`.
- Do not modify or stage unrelated files, including generated Codex runtime
  files.

## Activation and Verification

- Evaluate and build `.#homeConfigurations.chiendo97.activationPackage` before
  activation.
- Run `home-manager switch --flake .#chiendo97` so Home Manager unloads and
  removes the obsolete managed agent while activating the upgraded profile.
- Confirm `com.home-manager.auto-update` is absent from the user launchd domain
  and its managed plist is gone.
- Run `git diff --check` and review the final scoped diff.
