{ config, lib, pkgs, ... }:

{
  imports =
    [ ./hardware-configuration.nix
    ];

  # Bootloader
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  # Networking
  networking.hostName = "nixos-cle";
  networking.useDHCP = lib.mkDefault true;

  # Timezone & locale
  time.timeZone = "Asia/Ho_Chi_Minh";
  i18n.defaultLocale = "en_US.UTF-8";

  # User account
  users.users.cle = {
    isNormalUser = true;
    shell = pkgs.zsh;
    extraGroups = [ "wheel" "docker" ];
    openssh.authorizedKeys.keys = [
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILDumojeNQeQ590WBhI+m4LyeLwoiK1okP/fdLyabtG3 chiendo97@gmail.com"
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINjcLllQWX0DfhaSKDR5b4y2Ok/Y7lp7614GVvBv/kXM cle@nixos-cle"
    ];
  };

  # Enable zsh system-wide (required for user shell)
  programs.zsh.enable = true;

  # Passwordless sudo for wheel
  security.sudo.wheelNeedsPassword = false;

  # SSH
  services.openssh = {
    enable = true;
    settings = {
      PermitRootLogin = "no";
      PasswordAuthentication = false;
    };
  };

  # Tailscale
  services.tailscale.enable = true;

  # System packages
  environment.systemPackages = with pkgs; [
    vim
    git
    htop
    curl
    wget
  ];

  # Nix settings
  nix.settings.experimental-features = [ "nix-command" "flakes" ];

  # nix-ld: dynamic linker for generic Linux binaries (uv, etc.)
  programs.nix-ld.enable = true;

  # QEMU guest agent
  services.qemuGuest.enable = true;

  # Agenix secrets (system-level, uses host SSH key)
  age.secrets.wg_genbook_aws = {
    file = ../../secrets/wg_genbook_aws.age;
    mode = "600";
  };
  age.secrets.wg_urieljsc_office = {
    file = ../../secrets/wg_urieljsc_office.age;
    mode = "600";
  };

  # WireGuard VPN tunnels (auto-start on boot)
  networking.wg-quick.interfaces = {
    genbook-aws = {
      configFile = config.age.secrets.wg_genbook_aws.path;
      autostart = true;
    };
    urieljsc-office = {
      configFile = config.age.secrets.wg_urieljsc_office.path;
      autostart = true;
    };
  };

  # VirtioFS mounts from Unraid host
  fileSystems."/home/cle/Source/selfhost" = {
    device = "selfhost";
    fsType = "virtiofs";
  };
  fileSystems."/home/cle/Source/media" = {
    device = "media";
    fsType = "virtiofs";
  };

  # Firewall
  networking.firewall.enable = true;
  networking.firewall.allowedTCPPorts = [ 22 ];
  networking.firewall.trustedInterfaces = [ "tailscale0" ];

  system.stateVersion = "25.11";
}
