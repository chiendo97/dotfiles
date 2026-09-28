{ config, lib, pkgs, homeDirectory, username, ... }:

{
  home.username = username;
  home.homeDirectory = homeDirectory;
  home.stateVersion = "25.11";

  # ============================================================================
  # UV tools (Python CLIs in isolated venvs, managed outside Nix)
  # ============================================================================
  uvTools.tools = [
  ];

  home.activation.installUvPython =
    lib.hm.dag.entryAfter [ "writeBoundary" ] ''
      python3_bin="${config.home.homeDirectory}/.local/bin/python3"
      uv_python_root="${config.home.homeDirectory}/.local/share/uv/python"

      if [ -e "$python3_bin" ]; then
        target="$(readlink -f "$python3_bin" 2>/dev/null || true)"
        case "$target" in
          "$uv_python_root"/*)
            ;;
          *)
            echo "uv python: refusing to replace existing $python3_bin -> $target" >&2
            exit 1
            ;;
        esac
      fi

      ${pkgs.uv}/bin/uv python install 3 --default --upgrade
    '';

  # ============================================================================
  # Cargo tools (Rust CLIs, installed via cargo-binstall)
  # ============================================================================
  cargoTools.tools = [
    { crate = "mdterm"; }
    { crate = "xleak"; }
    { crate = "zsh-patina"; }
    { crate = "dua-cli"; }
    { crate = "harper-ls"; }
  ];

  # ============================================================================
  # Packages (no Home Manager module available)
  # ============================================================================
  home.packages =
    # Shared packages (all platforms)
    (import ./packages/core.nix { inherit pkgs; }) ++
    (import ./packages/development.nix { inherit pkgs; }) ++
    (import ./packages/database.nix { inherit pkgs; }) ++
    (import ./packages/containers.nix { inherit pkgs; }) ++
    (import ./packages/cloud.nix { inherit pkgs; }) ++
    (import ./packages/security.nix { inherit pkgs; }) ++
    # Pin to 1.27.1 — 1.27.0 had a bug where user@host renders as black (#706)
    [ (pkgs.pure-prompt.overrideAttrs (old: rec {
      version = "1.27.1";
      src = pkgs.fetchFromGitHub {
        owner = "sindresorhus";
        repo = "pure";
        rev = "v${version}";
        hash = "sha256-Fhk4nlVPS09oh0coLsBnjrKncQGE6cUEynzDO2Skiq8=";
      };
    })) ] ++
    # Platform-specific packages
    (lib.optionals pkgs.stdenv.isLinux (import ./packages/linux.nix { inherit pkgs; })) ++
    (lib.optionals pkgs.stdenv.isDarwin (import ./packages/darwin.nix { inherit pkgs; }));

  # ============================================================================
  # Config files
  # ============================================================================
  xdg.configFile."containers/registries.conf".text = ''
    unqualified-search-registries = ["docker.io"]
  '';

  xdg.configFile."containers/policy.json".text = builtins.toJSON {
    default = [{ type = "insecureAcceptAnything"; }];
  };

  # ============================================================================
  # Systemd user services (Linux only)
  # ============================================================================
  systemd.user.sockets.podman = lib.mkIf pkgs.stdenv.isLinux {
    Unit.Description = "Podman API Socket";
    Socket = {
      ListenStream = "%t/podman/podman.sock";
      SocketMode = "0660";
      TriggerLimitIntervalSec = "60s";
      TriggerLimitBurst = 10;
    };
    Install.WantedBy = [ "sockets.target" ];
  };

  systemd.user.services.podman = lib.mkIf pkgs.stdenv.isLinux {
    Unit.Description = "Podman API Service";
    Service = {
      Type = "exec";
      ExecStart = "${pkgs.podman}/bin/podman system service --time=120";
    };
  };

  # ============================================================================
  # Programs with Home Manager modules
  # ============================================================================
  programs.neovim = {
    enable = true;
    sideloadInitLua = true;
    withRuby = false;
    withPython3 = false;
  };

  programs.fzf = {
    enable = true;
    enableZshIntegration = true;
  };

  programs.zoxide = {
    enable = true;
    enableZshIntegration = true;
  };


  programs.go.enable = true;
  programs.eza.enable = true;
  programs.bat.enable = true;

  programs.ssh = {
    enable = true;
    enableDefaultConfig = false;

    settings = {
      "*" = {
        AddKeysToAgent = "yes";
      };

      "cle-home-server" = {
        HostName = "100.118.125.39";
        User = "cle";
      };

      "vng-gateway-01" = {
        HostName = "42.1.126.5";
        Port = 234;
        User = "cle";
        IdentityFile = "~/.ssh/id_ed25519_vng_gateway_01";
      };

      "cle-homic" = {
        HostName = "100.83.74.104";
        User = "root";
      };
    };
  };

  programs.gh = {
    enable = true;
    settings = {
      git_protocol = "ssh";
      editor = "nvim";
    };
  };

  programs.home-manager.enable = true;

  # ============================================================================
  # Zsh Configuration
  # ============================================================================
  programs.zsh = {
    enable = true;
    enableCompletion = true;
    completionInit = ''
      # Completion dump file
      zcompdump="''${XDG_CACHE_HOME:-$HOME/.cache}/zsh/zcompdump-$ZSH_VERSION"

      # Create cache directory if it doesn't exist
      [[ -d $(dirname "$zcompdump") ]] || mkdir -p "$(dirname "$zcompdump")"

      # Load and initialize completion system
      autoload -Uz compinit

      # Use cached completions unless dump is older than 24 hours
      if [[ -f "$zcompdump" && $(find "$zcompdump" -mtime -1 2>/dev/null) ]]; then
        compinit -C -d "$zcompdump"
      else
        compinit -d "$zcompdump"
        touch "$zcompdump"
      fi
    '';

    # History settings
    history = {
      size = 10000;
      ignoreDups = true;
      share = true;
    };

    # Shell aliases
    shellAliases = {
      # General
      l = "eza";
      t = "tree --gitignore";
      c = "clear";
      v = "vim";
      n = "nvim";
      nv = "nvim";
      ll = "eza -l";
      hssh = ''ssh -o ProxyCommand="nc -X 5 -x 127.0.0.1:1055 %h %p"'';

      # Git
      gi = "git";
      tx = "tmux";
      gf = "git fetch --all";
      gd = "git diff";
      gb = "git branch";
      gs = "git status";
      gl = "git log";

      # Go
      pp = "go tool pprof";
      vendor = "go mod vendor";
      tidy = "go mod tidy";

      # History backup/restore
      history-backup = "age -r \"$(cat ~/.ssh/id_ed25519_agenix.pub)\" -o ~/.config/home-manager/secrets/zsh_history.age ~/.zsh_history && echo 'History backed up'";
      history-restore = "age -d -i ~/.ssh/id_ed25519_agenix ~/.config/home-manager/secrets/zsh_history.age > ~/.zsh_history && echo 'History restored'";
    };

    # Session variables
    sessionVariables = {
      GO111MODULE = "auto";
      GOSUMDB = "off";
      DISCORD_GUILD_ID = "1181560951141584926";
    };

    profileExtra = lib.optionalString pkgs.stdenv.isDarwin ''
      # OrbStack command-line tools and integration
      source ~/.orbstack/shell/init.zsh 2>/dev/null || :
    '';

    # Zsh init content using lib.mkOrder for proper ordering
    initContent = lib.mkMerge [
      # Early init (source nix first)
      (lib.mkBefore ''
        # Source nix profile (multi-user or single-user install)
        if [ -e '/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh' ]; then
          . '/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh'
        elif [ -e "$HOME/.nix-profile/etc/profile.d/nix.sh" ]; then
          . "$HOME/.nix-profile/etc/profile.d/nix.sh"
        fi

        # Emacs keybindings (must be before fzf sets up ^I binding)
        bindkey -e
      '')

      # Main init content (runs after Home Manager sets up fpath)
      ''
        # Pure prompt (installed via home.packages, must be after fpath setup)
        autoload -U promptinit
        promptinit
        prompt pure

        # Edit command line with ^g
        autoload -U edit-command-line
        zle -N edit-command-line
        bindkey '^g' edit-command-line

        # Syntax highlighting via zsh-patina (Rust daemon, sub-ms highlighting)
        eval "$(zsh-patina activate)"
      ''
    ];

    envExtra = ''
      # Source nix profile early (in .zshenv) so nix is available in all shell types
      if [ -e '/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh' ]; then
        . '/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh'
      elif [ -e "$HOME/.nix-profile/etc/profile.d/nix.sh" ]; then
        . "$HOME/.nix-profile/etc/profile.d/nix.sh"
      fi
    '';

    autosuggestion.enable = true;
  };

  home.file."./.zprofile" = lib.mkIf pkgs.stdenv.isDarwin {
    force = true;
    target = ".zprofile";
  };

  # ============================================================================
  # Nix Configuration
  # ============================================================================
  nix.package = pkgs.nix;
  nix.settings.experimental-features = [ "nix-command" "flakes" ];

  # ============================================================================
  # Launchd Agents (macOS scheduled tasks)
  # ============================================================================
  launchd.agents.podman-machine = lib.mkIf pkgs.stdenv.isDarwin {
    enable = true;
    config = {
      Label = "com.podman.machine";
      ProgramArguments = [
        "/bin/sh"
        "-c"
        ''
          export PATH="$HOME/.nix-profile/bin:/nix/var/nix/profiles/default/bin:$PATH"
          podman machine start 2>&1 || true
        ''
      ];
      RunAtLoad = true;
      StandardOutPath = "/tmp/podman-machine.out.log";
      StandardErrorPath = "/tmp/podman-machine.err.log";
    };
  };

  # ============================================================================
  # Session Variables (available to all programs)
  # ============================================================================
  home.sessionVariables = {
    EDITOR = "nvim";
    LC_CTYPE = "en_US.UTF-8";
    ZK_NOTEBOOK_DIR = "/srv/selfhost/zk";
  } // lib.optionalAttrs pkgs.stdenv.isLinux {
    SSL_CERT_FILE = "/etc/ssl/certs/ca-certificates.crt";
    DOCKER_HOST = "unix:///run/user/1000/podman/podman.sock";
  } // lib.optionalAttrs pkgs.stdenv.isDarwin {
    DOCKER_HOST = "unix:///var/folders/s6/svtg9t310t167pdfqqcj4gvw0000gn/T/podman/podman-machine-default-api.sock";
  };

  home.sessionPath = [
    "$HOME/.local/bin"
    "$HOME/.cargo/bin"
    "$HOME/go/bin"
  ];

  home.file.".npmrc".text = ''
    prefix=${config.home.homeDirectory}/.local
  '';
}
