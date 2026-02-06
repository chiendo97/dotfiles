let
  # Your SSH public key - used to encrypt/decrypt secrets
  cle = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKeJL/S/PKfn776mEl9UQHr8lp8in2/npsL98YygHtXs cle@dotfiles";
in
{
  # API keys
  "api-keys.age".publicKeys = [ cle ];

  # Zsh history backup (manual restore, not auto-decrypted)
  "zsh_history.age".publicKeys = [ cle ];

  # Rclone config
  "rclone.age".publicKeys = [ cle ];

  # SSH private keys
  "aws_bastion_rsa.age".publicKeys = [ cle ];
  "cle_viettel_idc.age".publicKeys = [ cle ];
  "cle_vpn.age".publicKeys = [ cle ];
  "github_key.age".publicKeys = [ cle ];
  "github_rsa.age".publicKeys = [ cle ];
  "homic_olympus.age".publicKeys = [ cle ];
  "homic_rsa.age".publicKeys = [ cle ];
  "id_ed25519_github.age".publicKeys = [ cle ];
  "oracle.age".publicKeys = [ cle ];
  "uriel_rsa.age".publicKeys = [ cle ];
}
