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

  # QEMU guest agent
  services.qemuGuest.enable = true;

  # Firewall
  networking.firewall.enable = true;
  networking.firewall.allowedTCPPorts = [ 22 ];
  networking.firewall.trustedInterfaces = [ "tailscale0" ];

  system.stateVersion = "24.11";
}
