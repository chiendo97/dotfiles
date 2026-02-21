{ pkgs }:
with pkgs; [
  k9s
  kubectl
  kubetail
  podman
  podman-compose
  docker-client
]
