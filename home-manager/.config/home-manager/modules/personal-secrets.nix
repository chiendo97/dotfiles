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

  programs.ssh.settings = {
    "github.com" = {
      HostName = "github.com";
      IdentityFile = "~/.ssh/github_key";
      IdentitiesOnly = true;
    };

    "aws-dev" = {
      HostName = "10.26.136.50";
      User = "cle";
      IdentityFile = "~/.ssh/aws_bastion_rsa";
      IdentitiesOnly = true;
    };

    "cle-pve" = {
      HostName = "192.168.50.13";
      User = "root";
      IdentityFile = "~/.ssh/cle_pve";
    };

    "backup-pve" = {
      HostName = "192.168.50.53";
      User = "root";
      IdentityFile = "~/.ssh/id_ed25519_selfhost";
      IdentitiesOnly = true;
    };

    "pulse-pve" = {
      HostName = "192.168.50.18";
      User = "root";
      IdentityFile = "~/.ssh/id_ed25519_selfhost";
      IdentitiesOnly = true;
    };

    "plex-pve" = {
      HostName = "192.168.50.242";
      User = "root";
      IdentityFile = "~/.ssh/id_ed25519_selfhost";
      IdentitiesOnly = true;
    };

    "jellyfin-pve" = {
      HostName = "100.111.70.79";
      User = "root";
      IdentityFile = "~/.ssh/id_ed25519_selfhost";
      IdentitiesOnly = true;
    };

    "nas-pve" = {
      HostName = "192.168.50.244";
      User = "root";
      IdentityFile = "~/.ssh/id_ed25519_selfhost";
      IdentitiesOnly = true;
    };

    "frigate-pve" = {
      HostName = "192.168.50.245";
      User = "root";
      IdentityFile = "~/.ssh/id_ed25519_selfhost";
      IdentitiesOnly = true;
    };

    "immich-pve" = {
      HostName = "192.168.50.246";
      User = "root";
      IdentityFile = "~/.ssh/id_ed25519_selfhost";
      IdentitiesOnly = true;
    };

    "unraid-cle" = {
      HostName = "100.89.182.96";
      User = "root";
    };

    "cle-viettel" = {
      HostName = "171.244.62.91";
      User = "root";
      IdentityFile = "~/.ssh/cle_viettel_idc";
    };

    "homic-olympus" = {
      HostName = "100.69.202.110";
      User = "cle";
      IdentityFile = "~/.ssh/homic_olympus";
    };

    "oracle" = {
      HostName = "100.79.39.73";
      User = "ubuntu";
      IdentityFile = "~/.ssh/oracle";
    };

    # "nixos-cle" = {
    #   HostName = "192.168.50.55";
    #   User = "cle";
    #   IdentityFile = "~/.ssh/nixos_cle";
    # };

    "homelab-pve" = {
      HostName = "100.112.172.58";
      User = "cle";
      IdentityFile = "~/.ssh/homelab_pve";
    };

    "selfhost-pve" = {
      HostName = "100.81.144.82";
      User = "cle";
      IdentityFile = "~/.ssh/id_ed25519_selfhost";
      IdentitiesOnly = true;
    };
  };

  programs.zsh.initContent = ''
    # API Keys - managed by agenix
    source ~/.secrets/api-keys 2>/dev/null
    unset GITHUB_TOKEN
    unset ANTHROPIC_API_KEY
  '';

  # home.activation.dockerContextUnraidCle = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
  #   docker_bin="${pkgs.docker-client}/bin/docker"
  #   if "$docker_bin" context inspect unraid-cle >/dev/null 2>&1; then
  #     "$docker_bin" context update unraid-cle \
  #       --description "Unraid CLE Docker daemon" \
  #       --docker "host=ssh://root@unraid-cle" >/dev/null
  #   else
  #     "$docker_bin" context create unraid-cle \
  #       --description "Unraid CLE Docker daemon" \
  #       --docker "host=ssh://root@unraid-cle" >/dev/null
  #   fi
  # '';
}
