{ config, ... }:

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

  programs.ssh.matchBlocks = {
    "gitlab.com" = {
      hostname = "gitlab.com";
      identityFile = "~/.ssh/uriel_rsa";
      extraOptions = {
        PreferredAuthentications = "publickey";
      };
    };

    "github.com" = {
      hostname = "github.com";
      identityFile = "~/.ssh/id_ed25519_github";
    };

    "vng-dev" = {
      hostname = "100.64.0.37";
      port = 234;
      user = "cle";
      identityFile = "~/.ssh/id_ed25519_vng_dev";
    };

    "git.urieljsc.com" = {
      hostname = "git.urieljsc.com";
      user = "git";
      identityFile = "~/.ssh/id_ed25519_urieljsc_gitlab";
      identitiesOnly = true;
    };

    "urieljsc" = {
      hostname = "ssh.urieljsc.com";
      user = "chienle";
      identityFile = "~/.ssh/uriel_rsa";
      identitiesOnly = true;
    };
  };

  programs.zsh.initContent = ''
    # Uriel API Keys - managed by agenix
    source ~/.secrets/uriel-api-keys 2>/dev/null
    unset GITHUB_TOKEN
    unset ANTHROPIC_API_KEY
  '';
}
