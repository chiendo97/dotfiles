{ config, lib, ... }:

{
  age.identityPaths = lib.mkDefault [
    "${config.home.homeDirectory}/.ssh/id_ed25519_agenix"
  ];

  age.secrets.gemini-api-key = {
    file = ../secrets/gemini-api-key.age;
    path = "${config.home.homeDirectory}/.secrets/gemini-api-key";
    mode = "600";
  };

  programs.zsh.initContent = ''
    # Gemini API token - managed by agenix
    export GEMINI_API_KEY="$(<~/.secrets/gemini-api-key)"
  '';
}
