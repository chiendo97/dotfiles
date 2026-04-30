{ config, lib, pkgs, ... }:

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
    "homelab_pve"
    "id_ed25519_selfhost"
  ]);

  programs.ssh.matchBlocks = {
    "github.com" = {
      hostname = "github.com";
      identityFile = "~/.ssh/github_key";
      identitiesOnly = true;
    };

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

    "unraid-cle" = {
      hostname = "unraid-cle";
      user = "root";
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

    "homelab-pve" = {
      hostname = "192.168.50.130";
      user = "cle";
      identityFile = "~/.ssh/homelab_pve";
    };

    "selfhost-pve" = {
      hostname = "192.168.50.121";
      user = "cle";
      identityFile = "~/.ssh/id_ed25519_selfhost";
      identitiesOnly = true;
    };
  };

  programs.zsh.initContent = ''
    # API Keys - managed by agenix
    source ~/.secrets/api-keys 2>/dev/null
    unset GITHUB_TOKEN
    unset ANTHROPIC_API_KEY
  '';

  home.activation.dockerContextUnraidCle = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
    docker_bin="${pkgs.docker-client}/bin/docker"
    if "$docker_bin" context inspect unraid-cle >/dev/null 2>&1; then
      "$docker_bin" context update unraid-cle \
        --description "Unraid CLE Docker daemon" \
        --docker "host=ssh://root@unraid-cle" >/dev/null
    else
      "$docker_bin" context create unraid-cle \
        --description "Unraid CLE Docker daemon" \
        --docker "host=ssh://root@unraid-cle" >/dev/null
    fi
  '';
}
