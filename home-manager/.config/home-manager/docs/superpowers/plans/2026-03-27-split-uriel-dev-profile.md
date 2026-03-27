# Split uriel-dev Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split Home Manager config so aws-dev (uriel-dev) only decrypts work-related secrets with its own agenix identity key, keeping personal secrets isolated to nixos-cle.

**Architecture:** Extract all agenix config and secret-dependent SSH matchBlocks from `home.nix` into two new modules: `modules/uriel-secrets.nix` (work secrets, `id_ed25519_uriel_dev` key) and `modules/personal-secrets.nix` (personal secrets, `id_ed25519_agenix` key). Update `flake.nix` to compose these modules per host.

**Tech Stack:** Nix (Home Manager modules), agenix

**Spec:** `docs/superpowers/specs/2026-03-27-split-uriel-dev-profile-design.md`

---

### Task 1: Create `modules/uriel-secrets.nix`

**Files:**
- Create: `modules/uriel-secrets.nix`

- [ ] **Step 1: Create the module file**

```nix
{ config, ... }:

{
  age.identityPaths = [ "${config.home.homeDirectory}/.ssh/id_ed25519_uriel_dev" ];

  age.secrets = {
    rclone = {
      file = ../secrets/rclone.age;
      path = "${config.home.homeDirectory}/.config/rclone/rclone.conf";
    };
    wg_genbook_aws = {
      file = ../secrets/wg_genbook_aws.age;
      path = "${config.home.homeDirectory}/.config/wireguard/genbook-aws.conf";
      mode = "600";
    };
    wg_urieljsc_office = {
      file = ../secrets/wg_urieljsc_office.age;
      path = "${config.home.homeDirectory}/.config/wireguard/urieljsc-office.conf";
      mode = "600";
    };
  } // builtins.listToAttrs (map (name: {
    inherit name;
    value = {
      file = ../secrets + "/${name}.age";
      path = "${config.home.homeDirectory}/.ssh/${name}";
      mode = "600";
    };
  }) [
    "uriel_rsa"
    "id_ed25519_urieljsc_gitlab"
    "genbook-mono-deploy"
    "id_ed25519_github"
    "id_ed25519_vng_dev"
  ]);

  programs.ssh.matchBlocks = {
    "gitlab.com" = {
      hostname = "gitlab.com";
      identityFile = "~/.ssh/uriel_rsa";
      extraOptions = {
        PreferredAuthentications = "publickey";
      };
    };

    "github.com" = {
      hostname = "github.com";
      identityFile = "~/.ssh/id_ed25519_github";
    };

    "vng-dev" = {
      hostname = "100.64.0.37";
      port = 234;
      user = "cle";
      identityFile = "~/.ssh/id_ed25519_vng_dev";
    };

    "git.urieljsc.com" = {
      hostname = "git.urieljsc.com";
      user = "git";
      identityFile = "~/.ssh/id_ed25519_urieljsc_gitlab";
      identitiesOnly = true;
    };

    "urieljsc" = {
      hostname = "ssh.urieljsc.com";
      user = "chienle";
      identityFile = "~/.ssh/uriel_rsa";
      identitiesOnly = true;
    };
  };
}
```

- [ ] **Step 2: Commit**

```bash
git add modules/uriel-secrets.nix
git commit -m "feat: add uriel-secrets module with work-related secrets and SSH hosts"
```

---

### Task 2: Create `modules/personal-secrets.nix`

**Files:**
- Create: `modules/personal-secrets.nix`

- [ ] **Step 1: Create the module file**

```nix
{ config, lib, ... }:

{
  age.identityPaths = [ "${config.home.homeDirectory}/.ssh/id_ed25519_agenix" ];

  age.secrets = {
    api-keys = {
      file = ../secrets/api-keys.age;
      path = "${config.home.homeDirectory}/.secrets/api-keys";
    };
  } // builtins.listToAttrs (map (name: {
    inherit name;
    value = {
      file = ../secrets + "/${name}.age";
      path = "${config.home.homeDirectory}/.ssh/${name}";
      mode = "600";
    };
  }) [
    "aws_bastion_rsa"
    "github_key"
    "github_rsa"
    "cle_viettel_idc"
    "cle_vpn"
    "homic_olympus"
    "homic_rsa"
    "oracle"
    "nixos_cle"
  ]);

  programs.ssh.matchBlocks = {
    "aws-dev" = {
      hostname = "10.26.136.50";
      user = "cle";
      identityFile = "~/.ssh/aws_bastion_rsa";
      identitiesOnly = true;
    };

    "cle-viettel" = {
      hostname = "171.244.62.91";
      user = "root";
      identityFile = "~/.ssh/cle_viettel_idc";
    };

    "homic-olympus" = {
      hostname = "100.69.202.110";
      user = "cle";
      identityFile = "~/.ssh/homic_olympus";
    };

    "oracle" = {
      hostname = "168.138.176.219";
      user = "ubuntu";
      identityFile = "~/.ssh/oracle";
    };

    "nixos-cle" = {
      hostname = "192.168.50.55";
      user = "cle";
      identityFile = "~/.ssh/nixos_cle";
    };
  };

  programs.zsh.initContent = ''
    # API Keys - managed by agenix
    source ~/.secrets/api-keys 2>/dev/null
    unset GITHUB_TOKEN
  '';
}
```

- [ ] **Step 2: Commit**

```bash
git add modules/personal-secrets.nix
git commit -m "feat: add personal-secrets module with personal secrets and SSH hosts"
```

---

### Task 3: Strip secrets from `home.nix`

**Files:**
- Modify: `home.nix:8-54` (remove entire agenix section)
- Modify: `home.nix:170-260` (remove secret-dependent SSH matchBlocks, keep shared ones)
- Modify: `home.nix:507-522` (remove api-keys source from zsh initContent)

- [ ] **Step 1: Remove the agenix secrets section (lines 8-54)**

Replace the entire agenix block:

```
  # ============================================================================
  # Agenix secrets
  # ============================================================================
  age.identityPaths = [ "${config.home.homeDirectory}/.ssh/id_ed25519_agenix" ];

  age.secrets = {
    ...
  ]);
```

with nothing (delete the whole block from `# === Agenix secrets` through the closing `]);`).

- [ ] **Step 2: Remove secret-dependent SSH matchBlocks, keep shared ones**

The `programs.ssh.matchBlocks` should be reduced to only:

```nix
  programs.ssh = {
    enable = true;
    enableDefaultConfig = false;

    matchBlocks = {
      "*" = {
        addKeysToAgent = "yes";
      };

      "cle-home-server" = {
        hostname = "100.118.125.39";
        user = "cle";
      };

      "vng-gateway-01" = {
        hostname = "42.1.126.5";
        port = 234;
        user = "cle";
        identityFile = "~/.ssh/id_ed25519_vng_gateway_01";
      };

      "cle-homic" = {
        hostname = "100.83.74.104";
        user = "root";
      };
    };
  };
```

Removed matchBlocks: `gitlab.com`, `github.com`, `cle-viettel`, `homic-olympus`, `oracle`, `urieljsc`, `git.urieljsc.com`, `aws-dev`, `nixos-cle`, `vng-dev`.

- [ ] **Step 3: Remove api-keys source from zsh initContent**

In the zsh `initContent` second block (the main init content string), remove these 3 lines:

```
        # API Keys - managed by agenix
        source ~/.secrets/api-keys 2>/dev/null
        unset GITHUB_TOKEN
```

The closing `''` of that string should now come right after `bindkey '^g' edit-command-line`.

- [ ] **Step 4: Commit**

```bash
git add home.nix
git commit -m "refactor: remove secrets and secret-dependent SSH from home.nix"
```

---

### Task 4: Update `flake.nix` with new configurations

**Files:**
- Modify: `flake.nix:85-109` (homeConfigurations section)

- [ ] **Step 1: Update homeConfigurations**

Replace the `homeConfigurations` block with:

```nix
      homeConfigurations = {
        # Linux (x86_64) - username: cle
        "cle" = mkHomeConfiguration {
          system = "x86_64-linux";
          username = "cle";
          extraModules = [
            ./modules/personal-secrets.nix
            ./modules/uriel-secrets.nix
            ./profiles/genbook.nix
          ];
        };
        "cle@linux" = mkHomeConfiguration {
          system = "x86_64-linux";
          username = "cle";
          extraModules = [
            ./modules/personal-secrets.nix
            ./modules/uriel-secrets.nix
            ./profiles/genbook.nix
          ];
        };

        # Linux (x86_64) with extra genbook-specific modules
        "genbook" = mkHomeConfiguration {
          system = "x86_64-linux";
          username = "cle";
          extraModules = [
            ./modules/personal-secrets.nix
            ./modules/uriel-secrets.nix
            ./profiles/genbook.nix
          ];
        };

        # Linux (x86_64) - uriel dev machine (work secrets only, no personal secrets)
        "uriel-dev" = mkHomeConfiguration {
          system = "x86_64-linux";
          username = "cle";
          extraModules = [ ./modules/uriel-secrets.nix ];
        };

        # macOS (Apple Silicon) - username: chiendo97
        "chiendo97" = mkHomeConfiguration { system = "aarch64-darwin"; username = "chiendo97"; };
        "chiendo97@darwin" = mkHomeConfiguration { system = "aarch64-darwin"; username = "chiendo97"; };
        "chiendo97@macos" = mkHomeConfiguration { system = "aarch64-darwin"; username = "chiendo97"; };
      };
```

- [ ] **Step 2: Commit**

```bash
git add flake.nix
git commit -m "feat: add uriel-dev config, update cle/genbook to use secret modules"
```

---

### Task 5: Update `secrets/secrets.nix` with uriel-dev public key

**Files:**
- Modify: `secrets/secrets.nix`

- [ ] **Step 1: Add uriel-dev public key placeholder and update publicKeys**

Replace the entire file with:

```nix
let
  # Your SSH public key - used to encrypt/decrypt secrets
  cle = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKeJL/S/PKfn776mEl9UQHr8lp8in2/npsL98YygHtXs cle@dotfiles";

  # NixOS host key - needed for system-level agenix (WireGuard, etc.)
  nixos-cle = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOSnjSJMlot12qH5y87DmAMhwwKkSiK+iyLPaNdJh+Kc root@nixos-cle";

  # Uriel dev machine key - for work-related secrets on aws-dev
  # TODO: Replace with actual public key from aws-dev after running:
  #   ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_uriel_dev
  uriel-dev = "ssh-ed25519 PLACEHOLDER_REPLACE_WITH_ACTUAL_KEY";
in
{
  # === Personal secrets (cle key only) ===
  "api-keys.age".publicKeys = [ cle ];
  "zsh_history.age".publicKeys = [ cle ];

  # === Personal SSH keys (cle key only) ===
  "aws_bastion_rsa.age".publicKeys = [ cle ];
  "cle_viettel_idc.age".publicKeys = [ cle ];
  "cle_vpn.age".publicKeys = [ cle ];
  "github_key.age".publicKeys = [ cle ];
  "github_rsa.age".publicKeys = [ cle ];
  "homic_olympus.age".publicKeys = [ cle ];
  "homic_rsa.age".publicKeys = [ cle ];
  "oracle.age".publicKeys = [ cle ];
  "nixos_cle.age".publicKeys = [ cle ];

  # === Uriel/work secrets (cle + uriel-dev keys) ===
  "rclone.age".publicKeys = [ cle uriel-dev ];
  "uriel_rsa.age".publicKeys = [ cle uriel-dev ];
  "id_ed25519_urieljsc_gitlab.age".publicKeys = [ cle uriel-dev ];
  "genbook-mono-deploy.age".publicKeys = [ cle uriel-dev ];
  "id_ed25519_github.age".publicKeys = [ cle uriel-dev ];
  "id_ed25519_vng_dev.age".publicKeys = [ cle uriel-dev ];

  # === WireGuard configs (cle + uriel-dev + nixos-cle host key) ===
  "wg_genbook_aws.age".publicKeys = [ cle uriel-dev nixos-cle ];
  "wg_urieljsc_office.age".publicKeys = [ cle uriel-dev nixos-cle ];
}
```

Note: The `uriel-dev` key is a placeholder. After generating the key on aws-dev (Task 6), replace it and re-encrypt the affected `.age` files.

- [ ] **Step 2: Commit**

```bash
git add secrets/secrets.nix
git commit -m "feat: add uriel-dev key to secrets.nix, split secret ownership"
```

---

### Task 6: Verify the build (dry-run)

**Files:** None (verification only)

- [ ] **Step 1: Build the `cle` configuration (should succeed with both secret modules)**

```bash
home-manager build --flake .#cle
```

Expected: Build succeeds. All secrets and SSH matchBlocks are present from both modules.

- [ ] **Step 2: Build the `uriel-dev` configuration (should succeed with only uriel-secrets)**

```bash
home-manager build --flake .#uriel-dev
```

Expected: Build succeeds. Only work-related secrets and SSH matchBlocks are present.

- [ ] **Step 3: Build the `chiendo97` configuration (should succeed with no secrets)**

```bash
home-manager build --flake .#chiendo97
```

Expected: Build succeeds. No agenix secrets at all.

- [ ] **Step 4: Verify SSH config for uriel-dev has only work hosts**

```bash
cat $(home-manager build --flake .#uriel-dev --no-out-link)/home-files/.ssh/config
```

Expected output should contain: `gitlab.com`, `github.com`, `vng-dev`, `git.urieljsc.com`, `urieljsc`, `cle-home-server`, `vng-gateway-01`, `cle-homic`, and `*`. Should NOT contain: `cle-viettel`, `homic-olympus`, `oracle`, `nixos-cle`, `aws-dev`.

- [ ] **Step 5: Verify SSH config for cle has all hosts**

```bash
cat $(home-manager build --flake .#cle --no-out-link)/home-files/.ssh/config
```

Expected: All SSH matchBlocks from both modules plus shared ones in `home.nix`.

---

### Task 7: Manual steps (post-implementation)

These steps must be done by the user, not automated:

- [ ] **Step 1: Generate identity key on aws-dev**

SSH into aws-dev and run:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_uriel_dev -C "cle@uriel-dev"
cat ~/.ssh/id_ed25519_uriel_dev.pub
```

Copy the output public key.

- [ ] **Step 2: Replace placeholder in `secrets/secrets.nix`**

Replace `"ssh-ed25519 PLACEHOLDER_REPLACE_WITH_ACTUAL_KEY"` with the actual public key from Step 1.

- [ ] **Step 3: Re-encrypt the 8 uriel secrets**

For each of these files, decrypt with the cle key and re-encrypt with all required recipients:

```bash
cd secrets

# For each uriel secret (rclone, uriel_rsa, id_ed25519_urieljsc_gitlab,
# genbook-mono-deploy, id_ed25519_github, id_ed25519_vng_dev):
for secret in rclone uriel_rsa id_ed25519_urieljsc_gitlab genbook-mono-deploy id_ed25519_github id_ed25519_vng_dev; do
  age -d -i ~/.ssh/id_ed25519_agenix "${secret}.age" > "/tmp/${secret}.tmp"
  age -r "$(cat ~/.ssh/id_ed25519_agenix.pub)" \
      -r "URIEL_DEV_PUBKEY_HERE" \
      -o "${secret}.age" "/tmp/${secret}.tmp"
  rm "/tmp/${secret}.tmp"
done

# WireGuard secrets need 3 recipients (cle + uriel-dev + nixos-cle):
for secret in wg_genbook_aws wg_urieljsc_office; do
  age -d -i ~/.ssh/id_ed25519_agenix "${secret}.age" > "/tmp/${secret}.tmp"
  age -r "$(cat ~/.ssh/id_ed25519_agenix.pub)" \
      -r "URIEL_DEV_PUBKEY_HERE" \
      -r "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOSnjSJMlot12qH5y87DmAMhwwKkSiK+iyLPaNdJh+Kc root@nixos-cle" \
      -o "${secret}.age" "/tmp/${secret}.tmp"
  rm "/tmp/${secret}.tmp"
done
```

Replace `URIEL_DEV_PUBKEY_HERE` with the actual public key.

- [ ] **Step 4: Commit re-encrypted secrets**

```bash
git add secrets/secrets.nix secrets/*.age
git commit -m "feat: re-encrypt uriel secrets with uriel-dev key"
```

- [ ] **Step 5: Deploy on uriel-dev**

```bash
home-manager switch --flake .#uriel-dev
```

- [ ] **Step 6: Deploy on nixos-cle**

```bash
home-manager switch --flake .#cle
```
