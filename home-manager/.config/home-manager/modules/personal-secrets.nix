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
    "cle_pve"
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

    "cle-pve" = {
      hostname = "192.168.50.13";
      user = "root";
      identityFile = "~/.ssh/cle_pve";
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
    unset ANTHROPIC_API_KEY
  '';
}
