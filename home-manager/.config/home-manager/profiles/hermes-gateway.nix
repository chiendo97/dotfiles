{ lib, ... }:

{
  # Host-local values for the Hermes gateway account.
  home.sessionVariables = {
    ZK_NOTEBOOK_DIR = lib.mkForce "/home/hermes/zk";
    DOCKER_HOST = lib.mkForce "unix:///run/user/1002/podman/podman.sock";
  };
}