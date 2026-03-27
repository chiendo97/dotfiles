let
  # Your SSH public key - used to encrypt/decrypt secrets
  cle = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKeJL/S/PKfn776mEl9UQHr8lp8in2/npsL98YygHtXs cle@dotfiles";

  # NixOS host key - needed for system-level agenix (WireGuard, etc.)
  nixos-cle = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOSnjSJMlot12qH5y87DmAMhwwKkSiK+iyLPaNdJh+Kc root@nixos-cle";

  # Uriel dev machine key - for work-related secrets on aws-dev
  uriel-dev = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILvvaSiAV2bFJgiEiSPZswFq/j4lDBB0WoDu7/talMJN cle@uriel-dev";
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
