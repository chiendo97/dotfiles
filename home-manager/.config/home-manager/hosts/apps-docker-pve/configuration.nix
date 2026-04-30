{ config, lib, pkgs, modulesPath, ... }:

let
  selfhostComposeServices = [
    "bazarr"
    "dockerproxy"
    "dockge"
    "dockhand"
    "dozzle"
    "filebrowser"
    "flaresolverr"
    "hledger-webapp"
    "homepage"
    "openspeedtest"
    "playwright-mcp"
    "prowlarr"
    "qbittorrent"
    "radarr"
    "sabnzbd"
    "silverbullet"
    "sonarr"
    "speedtest-tracker"
    "syncthing"
    "tailscale-mcp"
    "traefik"
  ];
  selfhostComposeServiceArgs = lib.concatStringsSep " " selfhostComposeServices;
in
{
  imports = [
    (modulesPath + "/profiles/qemu-guest.nix")
  ];

  boot.loader.grub.enable = lib.mkDefault true;
  boot.loader.grub.device = lib.mkDefault "/dev/vda";
  boot.loader.timeout = lib.mkDefault 1;
  boot.growPartition = true;

  boot.initrd.availableKernelModules = [
    "ata_piix"
    "uhci_hcd"
    "virtio_pci"
    "virtio_blk"
    "virtio_scsi"
    "sr_mod"
  ];

  fileSystems."/" = lib.mkDefault {
    device = "/dev/disk/by-label/nixos";
    fsType = "ext4";
    autoResize = true;
  };

  networking.hostName = "selfhost-pve";
  networking.useDHCP = false;
  systemd.network.enable = true;
  systemd.network.networks."10-uplink" = {
    matchConfig.Name = "en*";
    address = [ "192.168.50.121/24" ];
    gateway = [ "192.168.50.1" ];
    dns = [ "192.168.50.1" "1.1.1.1" ];
    networkConfig.IPv6AcceptRA = true;
  };

  time.timeZone = "Asia/Ho_Chi_Minh";
  i18n.defaultLocale = "en_US.UTF-8";

  users.users.cle = {
    isNormalUser = true;
    shell = pkgs.zsh;
    extraGroups = [ "wheel" "docker" ];
    openssh.authorizedKeys.keys = [
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILDumojeNQeQ590WBhI+m4LyeLwoiK1okP/fdLyabtG3 chiendo97@gmail.com"
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKeJL/S/PKfn776mEl9UQHr8lp8in2/npsL98YygHtXs cle@dotfiles"
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOVcDy2hyrI2LjC4rUx1LGtHdg0iCYCXRfWwjmvR3goa cle@n100-selfhost-20260430"
    ];
  };

  programs.zsh.enable = true;
  programs.zsh.enableCompletion = false;
  security.sudo.wheelNeedsPassword = false;

  services.openssh = {
    enable = true;
    settings = {
      PermitRootLogin = "no";
      PasswordAuthentication = false;
    };
  };

  services.qemuGuest.enable = true;

  age.secrets.tailscale_selfhost_pve_auth_key = {
    file = ../../secrets/tailscale_selfhost_pve_auth_key.age;
    owner = "root";
    group = "root";
    mode = "0400";
  };

  services.tailscale = {
    enable = true;
    authKeyFile = config.age.secrets.tailscale_selfhost_pve_auth_key.path;
    extraUpFlags = [ "--hostname=selfhost-pve" "--ssh" ];
  };

  virtualisation.docker = {
    enable = true;
    autoPrune = {
      enable = true;
      dates = "weekly";
      flags = [ "--all" ];
    };
    daemon.settings = {
      log-driver = "json-file";
      log-opts = {
        max-size = "10m";
        max-file = "3";
      };
    };
  };

  boot.supportedFilesystems = [ "nfs" ];
  services.rpcbind.enable = true;

  systemd.tmpfiles.rules = [
    "d /srv/selfhost 0755 root root -"
    "d /mnt/user 0755 root root -"
    "d /mnt/user/selfhost 0755 root root -"
    "d /mnt/user/media 0755 root root -"
    "d /mnt/user/frigate 0755 root root -"
  ];

  fileSystems."/mnt/user/selfhost" = {
    device = "/srv/selfhost";
    fsType = "none";
    options = [ "bind" ];
  };

  fileSystems."/mnt/user/media" = {
    device = "192.168.50.244:/media";
    fsType = "nfs4";
    options = [
      "rw"
      "_netdev"
      "nofail"
      "x-systemd.automount"
      "x-systemd.idle-timeout=600"
      "vers=4.2"
    ];
  };

  fileSystems."/mnt/user/frigate" = {
    device = "192.168.50.244:/frigate";
    fsType = "nfs4";
    options = [
      "ro"
      "_netdev"
      "nofail"
      "x-systemd.automount"
      "x-systemd.idle-timeout=600"
      "vers=4.2"
    ];
  };

  systemd.services.selfhost-compose = {
    description = "Selfhost Docker Compose stack";
    after = [
      "docker.service"
      "network-online.target"
      "mnt-user-media.automount"
      "mnt-user-frigate.automount"
    ];
    wants = [ "network-online.target" ];
    requires = [ "docker.service" ];
    unitConfig.ConditionPathExists = "/srv/selfhost/docker-compose.yml";
    path = [ pkgs.docker pkgs.docker-compose ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      WorkingDirectory = "/srv/selfhost";
      ExecStart = "${pkgs.docker-compose}/bin/docker-compose up -d --remove-orphans ${selfhostComposeServiceArgs}";
      ExecStop = "${pkgs.docker-compose}/bin/docker-compose down";
      TimeoutStartSec = 0;
      TimeoutStopSec = 300;
    };
  };

  environment.systemPackages = with pkgs; [
    vim
    git
    htop
    curl
    wget
    jq
    ripgrep
    rsync
    dnsutils
    mtr
    tcpdump
    docker-compose
  ];

  nix.settings = {
    experimental-features = [ "nix-command" "flakes" ];
    trusted-users = [ "root" "cle" ];
  };

  programs.nix-ld.enable = true;
  programs.nix-ld.libraries = with pkgs; [
    fuse
    fuse3
  ];
  environment.sessionVariables.LD_LIBRARY_PATH = [ "/run/current-system/sw/share/nix-ld/lib" ];

  # Match the current Debian VM behavior during migration. Docker and Traefik
  # own the exposed service surface; tighten this after cutover if needed.
  networking.firewall.enable = false;

  system.stateVersion = "25.11";
}
