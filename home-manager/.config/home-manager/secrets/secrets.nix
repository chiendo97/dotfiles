let
  # Your SSH public key - used to encrypt/decrypt secrets
  cle = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKeJL/S/PKfn776mEl9UQHr8lp8in2/npsL98YygHtXs cle@dotfiles";
in
{
  # API keys
  "api-keys.age".publicKeys = [ cle ];

  # SSH private keys (for other machines)
  # "ssh-key-work.age".publicKeys = [ cle ];
  # "ssh-key-server.age".publicKeys = [ cle ];
}
