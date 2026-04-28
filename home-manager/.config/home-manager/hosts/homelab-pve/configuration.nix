{ config, lib, pkgs, modulesPath, ... }:

{
  imports = [
    # hardware-configuration.nix is included by the nixosConfigurations entry
    # only — the proxmox-image format provides its own root-fs config when
    # building the VMA artifact, so we keep this file out of the image path.
  ];

  # Bootloader — BIOS/grub on the virtio disk Proxmox attaches to imported VMs.
  boot.loader.grub.enable = lib.mkDefault true;
  boot.loader.grub.device = lib.mkDefault "/dev/vda";
  boot.loader.timeout = lib.mkDefault 1;

  # Auto-grow root partition on first boot from a fresh image — only relevant
  # when (re)building the proxmox-image artifact.
  boot.growPartition = true;

  # Networking
  networking.hostName = "homelab-pve";
  networking.useDHCP = lib.mkDefault true;

  # The nixos-generators proxmox format leaves systemd-networkd enabled but
  # without any .network units (it expects cloud-init to drop them in). Since
  # we don't use cloud-init, configure DHCP on the first virtio NIC explicitly.
  systemd.network.networks."10-uplink" = {
    matchConfig.Name = "ens18";
    networkConfig.DHCP = "yes";
  };

  # Timezone & locale
  time.timeZone = "Asia/Ho_Chi_Minh";
  i18n.defaultLocale = "en_US.UTF-8";

  # User account — same SSH keys as nixos-cle so you can log in immediately.
  users.users.cle = {
    isNormalUser = true;
    shell = pkgs.zsh;
    extraGroups = [ "wheel" ];
    openssh.authorizedKeys.keys = [
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILDumojeNQeQ590WBhI+m4LyeLwoiK1okP/fdLyabtG3 chiendo97@gmail.com"
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINjcLllQWX0DfhaSKDR5b4y2Ok/Y7lp7614GVvBv/kXM cle@nixos-cle"
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

  # Tailscale for remote access — you'll need to `tailscale up` once after first boot.
  services.tailscale.enable = true;

  # QEMU guest agent — lets Proxmox see VM IP, do clean shutdowns, etc.
  services.qemuGuest.enable = true;

  environment.systemPackages = with pkgs; [
    vim
    git
    htop
    curl
    wget
    dnsutils
    mtr
  ];

  nix.settings.experimental-features = [ "nix-command" "flakes" ];

  networking.firewall.enable = true;
  networking.firewall.allowedTCPPorts = [ 22 ];
  networking.firewall.trustedInterfaces = [ "tailscale0" ];

  system.stateVersion = "25.11";
}
