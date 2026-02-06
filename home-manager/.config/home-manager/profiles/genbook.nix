{ config, pkgs, ... }:

{
  age.secrets.rclone = {
    file = ../secrets/rclone.age;
    path = "${config.home.homeDirectory}/.config/rclone/rclone.conf";
  };

  systemd.user.services.rclone-gdrive = {
    Unit = {
      Description = "Rclone mount for Google Drive";
      After = [ "network-online.target" "agenix.service" ];
    };
    Service = {
      Type = "notify";
      ExecStartPre = "/usr/bin/env mkdir -p %h/Source/gdrive";
      ExecStart = ''
        ${pkgs.rclone}/bin/rclone mount gdrive: %h/Source/gdrive \
          --vfs-cache-mode full \
          --vfs-read-chunk-size 64M \
          --vfs-cache-max-size 10G \
          --dir-cache-time 30m \
          --poll-interval 30s \
          --drive-chunk-size 64M \
          --buffer-size 128M
      '';
      ExecStop = "/usr/bin/fusermount -u %h/Source/gdrive";
      Restart = "on-failure";
      RestartSec = 5;
    };
    Install = {
      WantedBy = [ "default.target" ];
    };
  };

  systemd.user.services.rclone-s3-genbook = {
    Unit = {
      Description = "Rclone mount for S3 genbook";
      After = [ "network-online.target" "agenix.service" ];
    };
    Service = {
      Type = "notify";
      ExecStartPre = "/usr/bin/env mkdir -p %h/Source/s3-genbook";
      ExecStart = ''
        ${pkgs.rclone}/bin/rclone mount s3-genbook:genbook-bk01 %h/Source/s3-genbook \
          --vfs-cache-mode full
      '';
      ExecStop = "/usr/bin/fusermount -u %h/Source/s3-genbook";
      Restart = "on-failure";
      RestartSec = 5;
    };
    Install = {
      WantedBy = [ "default.target" ];
    };
  };
}
