# Split uriel-dev Profile from Shared Home Manager Config

**Date:** 2026-03-27
**Status:** Approved

## Problem

The `cle` Home Manager config is shared between nixos-cle (personal workstation) and aws-dev (shared/multi-tenant genbook dev machine). This is dangerous because:

1. aws-dev is a shared machine — personal secrets (SSH keys, API keys) should not be decrypted there.
2. The agenix identity key (`id_ed25519_agenix`) is not and should not be on aws-dev.
3. `home-manager switch` currently fails on aws-dev because it can't decrypt secrets.

## Solution: Module Extraction (Approach B + separate agenix identity)

Extract secrets from `home.nix` into two modules. aws-dev gets its own agenix identity key (`id_ed25519_uriel_dev`) and only decrypts work-related secrets.

## New Files

### `modules/uriel-secrets.nix`

Agenix identity: `~/.ssh/id_ed25519_uriel_dev`

**Secrets (age.secrets):**
- `rclone`
- `wg_genbook_aws`
- `wg_urieljsc_office`

**SSH keys (age.secrets):**
- `uriel_rsa`
- `id_ed25519_urieljsc_gitlab`
- `genbook-mono-deploy`
- `id_ed25519_github`
- `id_ed25519_vng_dev`

**SSH matchBlocks:**
- `gitlab.com` — identityFile changed from `homic_rsa` to `uriel_rsa`
- `github.com` — identityFile `id_ed25519_github`
- `vng-dev` — identityFile `id_ed25519_vng_dev`
- `git.urieljsc.com` — identityFile `id_ed25519_urieljsc_gitlab`
- `urieljsc` — identityFile `uriel_rsa`

### `modules/personal-secrets.nix`

Agenix identity: `~/.ssh/id_ed25519_agenix`

**Secrets (age.secrets):**
- `api-keys`

**SSH keys (age.secrets):**
- `aws_bastion_rsa`
- `github_key`
- `github_rsa`
- `cle_viettel_idc`
- `cle_vpn`
- `homic_olympus`
- `homic_rsa`
- `oracle`
- `nixos_cle`

**SSH matchBlocks:**
- `aws-dev` — identityFile `aws_bastion_rsa`
- `cle-viettel`
- `homic-olympus`
- `oracle`
- `nixos-cle`

**Zsh init:**
- `source ~/.secrets/api-keys 2>/dev/null` + `unset GITHUB_TOKEN`

## Changes to Existing Files

### `home.nix`

**Remove:**
- All `age.identityPaths` config
- All `age.secrets` config
- All SSH matchBlocks that moved to secrets modules
- `source ~/.secrets/api-keys` from zsh initContent

**Keep:**
- SSH matchBlocks: `*`, `cle-home-server`, `cle-homic`, `vng-gateway-01`
- Everything else: packages, programs, systemd, launchd, session variables, etc.

### `secrets/secrets.nix`

**Add:** `uriel-dev` public key variable (from `id_ed25519_uriel_dev.pub` on aws-dev).

**Re-encrypt with both `cle` + `uriel-dev` keys:**
- `rclone.age`
- `wg_genbook_aws.age`
- `wg_urieljsc_office.age`
- `uriel_rsa.age`
- `id_ed25519_urieljsc_gitlab.age`
- `genbook-mono-deploy.age`
- `id_ed25519_github.age`
- `id_ed25519_vng_dev.age`

All other secrets remain encrypted with `cle` key only.

### `flake.nix`

**Add `uriel-dev` configuration:**

```nix
"uriel-dev" = mkHomeConfiguration {
  system = "x86_64-linux";
  username = "cle";
  extraModules = [ ./modules/uriel-secrets.nix ];
};
```

**Update existing configs to import both secret modules:**

```nix
"cle" = mkHomeConfiguration {
  system = "x86_64-linux";
  username = "cle";
  extraModules = [
    ./modules/personal-secrets.nix
    ./modules/uriel-secrets.nix
    ./profiles/genbook.nix
  ];
};
```

Same for `cle@linux` and `genbook`.

### `profiles/genbook.nix`

No changes — still provides rclone mount services only.

## Final Configuration Matrix

| Config | Modules | Agenix Keys |
|--------|---------|-------------|
| `cle` / `cle@linux` / `genbook` | home.nix + personal-secrets + uriel-secrets + genbook profile | Both identity keys |
| `uriel-dev` | home.nix + uriel-secrets | `id_ed25519_uriel_dev` only |
| `chiendo97` (macOS) | home.nix only | None |

## Manual Steps Required

1. Generate `id_ed25519_uriel_dev` key on aws-dev machine: `ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_uriel_dev`
2. Copy the public key to `secrets/secrets.nix`
3. Re-encrypt the 8 uriel secrets with both public keys using `age`
4. On nixos-cle: copy `id_ed25519_uriel_dev` public key or ensure both identity keys are present for the `cle` config to decrypt everything
