{ config, lib, ... }:

{
  age.identityPaths = [ "${config.home.homeDirectory}/.ssh/id_ed25519_uriel_dev" ];

  age.secrets = {
    uriel-api-keys = {
      file = ../secrets/uriel-api-keys.age;
      path = "${config.home.homeDirectory}/.secrets/uriel-api-keys";
      mode = "600";
    };
    rclone = {
      file = ../secrets/rclone.age;
      path = "${config.home.homeDirectory}/.config/rclone/rclone.conf";
    };
    wg_genbook_aws = {
      file = ../secrets/wg_genbook_aws.age;
      path = "${config.home.homeDirectory}/.config/wireguard/genbook-aws.conf";
      mode = "600";
    };
    wg_urieljsc_office = {
      file = ../secrets/wg_urieljsc_office.age;
      path = "${config.home.homeDirectory}/.config/wireguard/urieljsc-office.conf";
      mode = "600";
    };
    wg_colo = {
      file = ../secrets/wg_colo.age;
      path = "${config.home.homeDirectory}/.config/wireguard/colo.conf";
      mode = "600";
    };
  } // builtins.listToAttrs (map (name: {
    inherit name;
    value = {
      file = ../secrets + "/${name}.age";
      path = "${config.home.homeDirectory}/.ssh/${name}";
      mode = "600";
    };
  }) [
    "uriel_rsa"
    "id_ed25519_urieljsc_gitlab"
    "genbook-mono-deploy"
    "id_ed25519_github"
    "id_ed25519_vng_dev"
  ]);

  programs.ssh.settings = {
    "gitlab.com" = {
      HostName = "gitlab.com";
      IdentityFile = "~/.ssh/uriel_rsa";
      PreferredAuthentications = "publickey";
    };

    "github.com" = {
      HostName = "github.com";
      IdentityFile = lib.mkDefault "~/.ssh/id_ed25519_github";
    };

    "github-uriel" = {
      HostName = "github.com";
      User = "git";
      IdentityFile = "~/.ssh/id_ed25519_github";
      IdentitiesOnly = true;
    };

    "vng-dev" = {
      HostName = "10.100.20.11";
      User = "chienle";
      IdentityFile = "~/.ssh/id_ed25519_vng_dev";
      IdentitiesOnly = true;
    };

    "zariel-sv01" = {
      HostName = "100.64.0.98";
      User = "chienle";
      IdentityFile = "~/.ssh/id_ed25519_vng_dev";
      IdentitiesOnly = true;
    };

    "git.urieljsc.com" = {
      HostName = "git.urieljsc.com";
      User = "git";
      IdentityFile = "~/.ssh/id_ed25519_urieljsc_gitlab";
      IdentitiesOnly = true;
    };

    "urieljsc" = {
      HostName = "ssh.urieljsc.com";
      User = "chienle";
      IdentityFile = "~/.ssh/uriel_rsa";
      IdentitiesOnly = true;
    };

    "100.64.0.6" = {
      HostName = "100.64.0.6";
      User = "chienle";
      IdentityFile = "~/.ssh/uriel_rsa";
      IdentitiesOnly = true;
    };
  };

  programs.zsh.initContent = ''
    # Uriel API Keys - managed by agenix
    source ~/.secrets/uriel-api-keys 2>/dev/null
    unset GITHUB_TOKEN
    unset ANTHROPIC_API_KEY
  '';
}
