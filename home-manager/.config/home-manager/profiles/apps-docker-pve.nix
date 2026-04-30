{ lib, ... }:

{
  home.sessionVariables.DOCKER_HOST = lib.mkForce "unix:///var/run/docker.sock";

  systemd.user.sockets.podman.Install.WantedBy = lib.mkForce [ ];
}
