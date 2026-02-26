{ config, lib, pkgs, homeDirectory, username, ... }:

{
  home.username = username;
  home.homeDirectory = homeDirectory;
  home.stateVersion = "25.11";

  # ============================================================================
  # Agenix secrets
  # ============================================================================
  age.identityPaths = [ "${config.home.homeDirectory}/.ssh/id_ed25519_agenix" ];

  age.secrets = {
    api-keys = {
      file = ./secrets/api-keys.age;
      path = "${config.home.homeDirectory}/.secrets/api-keys";
    };
    rclone = {
      file = ./secrets/rclone.age;
      path = "${config.home.homeDirectory}/.config/rclone/rclone.conf";
    };
    wg_genbook_aws = {
      file = ./secrets/wg_genbook_aws.age;
      path = "${config.home.homeDirectory}/.config/wireguard/genbook-aws.conf";
      mode = "600";
    };
    wg_urieljsc_office = {
      file = ./secrets/wg_urieljsc_office.age;
      path = "${config.home.homeDirectory}/.config/wireguard/urieljsc-office.conf";
      mode = "600";
    };
  } // builtins.listToAttrs (map (name: {
    inherit name;
    value = {
      file = ./secrets + "/${name}.age";
      path = "${config.home.homeDirectory}/.ssh/${name}";
      mode = "600";
    };
  }) [
    "aws_bastion_rsa"
    "cle_viettel_idc"
    "cle_vpn"
    "github_key"
    "github_rsa"
    "homic_olympus"
    "homic_rsa"
    "id_ed25519_github"
    "oracle"
    "uriel_rsa"
    "nixos_cle"
  ]);

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
    (import ./packages/ai.nix { inherit pkgs; }) ++
    (import ./packages/security.nix { inherit pkgs; }) ++
    [ pkgs.pure-prompt ] ++
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
    Socket.ListenStream = "%t/podman/podman.sock";
    Install.WantedBy = [ "sockets.target" ];
  };

  # ============================================================================
  # Programs with Home Manager modules
  # ============================================================================
  programs.neovim.enable = true;

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

    matchBlocks = {
      "*" = {
        addKeysToAgent = "yes";
      };
      "gitlab.com" = {
        hostname = "gitlab.com";
        identityFile = "~/.ssh/homic_rsa";
        extraOptions = {
          PreferredAuthentications = "publickey";
        };
      };

      "github.com" = {
        hostname = "github.com";
        identityFile = "~/.ssh/id_ed25519_github";
      };

      "cle-home-server" = {
        hostname = "100.118.125.39";
        user = "cle";
      };

      "cle-viettel" = {
        hostname = "171.244.62.91";
        user = "root";
        identityFile = "~/.ssh/cle_viettel_idc";
      };

      "cle-homic" = {
        hostname = "100.83.74.104";
        user = "root";
      };

      "homic-olympus" = {
        hostname = "100.69.202.110";
        user = "cle";
        identityFile = "~/.ssh/homic_olympus";
      };

      "oracle" = {
        hostname = "168.138.176.219";
        user = "ubuntu";
        identityFile = "~/.ssh/oracle";
      };

      "urieljsc" = {
        hostname = "ssh.urieljsc.com";
        user = "chienle";
        identityFile = "~/.ssh/uriel_rsa";
        identitiesOnly = true;
      };

      "aws-dev" = {
        hostname = "10.26.136.50";
        user = "cle";
        identityFile = "~/.ssh/aws_bastion_rsa";
        identitiesOnly = true;
      };

      "nixos-cle" = {
        hostname = "192.168.50.55";
        user = "cle";
        identityFile = "~/.ssh/nixos_cle";
      };
    };
  };

  programs.tmux = {
    enable = true;
    mouse = true;
    keyMode = "vi";
    escapeTime = 0;
    baseIndex = 1;
    prefix = "C-Space";
    terminal = "xterm-256color";
    historyLimit = 5000;
    sensibleOnTop = true;

    plugins = with pkgs.tmuxPlugins; [
      cpu
      prefix-highlight
      yank
      {
        plugin = mkTmuxPlugin {
          pluginName = "tmux-buffer";
          version = "unstable";
          rtpFilePath = "buffex.tmux";
          src = pkgs.fetchFromGitHub {
            owner = "chiendo97";
            repo = "tmux-buffer";
            rev = "d5d82274203a8bc5b36b3065ae8d6db713a7b543";
            sha256 = "sha256-fpocaxq32+Ls6qnny32kAZdRtWXb/tFx1pMMdnQF2Hk=";
          };
        };
      }
    ];

    extraConfig = ''
      # === General ===
      set -g allow-rename off
      set -g detach-on-destroy off
      # baseIndex only sets base-index, not pane-base-index
      set -g pane-base-index 1
      set -as terminal-features ',xterm-256color:RGB:clipboard'
      set -g renumber-windows on
      set -g set-titles on
      set -g set-titles-string "#{session_name}"
      set-option -s set-clipboard on
      set -g allow-passthrough on

      # === Key Bindings ===
      unbind Space

      # Reload config
      unbind r
      bind r source-file ~/.config/tmux/tmux.conf \; display "Configuration Reloaded!"

      # Vim-tmux navigator integration
      is_vim="ps -o state= -o comm= -t '#{pane_tty}' \
          | grep -iqE '^[^TXZ ]+ +(\\S+\\/)?g?(view|n?vim?x?)(diff)?$'"
      bind-key -n 'C-h' if-shell "$is_vim" 'send-keys C-h'  'select-pane -L'
      bind-key -n 'C-j' if-shell "$is_vim" 'send-keys C-j'  'select-pane -D'
      bind-key -n 'C-k' if-shell "$is_vim" 'send-keys C-k'  'select-pane -U'
      bind-key -n 'C-l' if-shell "$is_vim" 'send-keys C-l'  'select-pane -R'

      bind-key -T copy-mode-vi 'C-h' select-pane -L
      bind-key -T copy-mode-vi 'C-j' select-pane -D
      bind-key -T copy-mode-vi 'C-k' select-pane -U
      bind-key -T copy-mode-vi 'C-l' select-pane -R
      bind-key -T copy-mode-vi 'C-\' select-pane -l

      # Zoom with Ctrl-z
      bind-key -n 'C-z' resize-pane -Z

      # Switch to last session
      unbind BSpace
      bind-key BSpace switch-client -l

      # Split panes
      unbind =
      unbind -
      bind = split-window -h -c '#{pane_current_path}'
      bind - split-window -v -c '#{pane_current_path}'

      # Resize panes
      bind-key -r H resize-pane -L
      bind-key -r J resize-pane -D
      bind-key -r K resize-pane -U
      bind-key -r L resize-pane -R

      # Synchronize panes
      bind-key C-a setw synchronize-panes

      # Copy mode
      bind-key -T copy-mode-vi v send-keys -X begin-selection
      bind v copy-mode

      # Window navigation
      bind-key -n M-h previous-window
      bind-key -n M-l next-window

      # Session switcher with fzf
      unbind -n C-s
      bind -n C-s run-shell -b "tmux list-sessions -F \"##S\" | fzf-tmux -h --layout=reverse | xargs tmux switch -t"

      # Swap windows
      bind-key -n C-S-Left swap-window -d -t -1
      bind-key -n C-S-Right swap-window -d -t +1

      # === Theme: Gruvbox Dark ===
      set-option -g status "on"
      set-option -g status-style bg=colour237,fg=colour223
      set-window-option -g window-status-style bg=colour214,fg=colour237
      set-window-option -g window-status-activity-style bg=colour237,fg=colour248
      set-window-option -g window-status-current-style bg=red,fg=colour237
      set-option -g pane-active-border-style fg=colour214
      set-option -g pane-border-style fg=colour237

      # Dim inactive panes, keep active pane at default
      set-option -g window-style 'fg=colour246,bg=colour233'
      set-option -g window-active-style 'fg=colour223,bg=colour235'
      set-option -g message-style bg=colour239,fg=colour223
      set-option -g message-command-style bg=colour239,fg=colour223
      set-option -g display-panes-active-colour colour250
      set-option -g display-panes-colour colour237
      set-window-option -g clock-mode-colour colour109
      set-window-option -g window-status-bell-style bg=colour167,fg=colour235

      # Status bar
      set-option -g status-justify "left"
      set-option -g status-left-style none
      set-option -g status-left-length "80"
      set-option -g status-right-style none
      set-option -g status-right-length "80"
      set-window-option -g window-status-separator ""

      set-option -g status-left "#[bg=colour241,fg=colour248] #S #[bg=colour237,fg=colour241,nobold,noitalics,nounderscore]"
      set-option -g status-right "#{prefix_highlight} #[bg=colour237,fg=colour239 nobold, nounderscore, noitalics]#[bg=colour239,fg=colour246] %Y-%m-%d  %H:%M #[bg=colour239,fg=colour248,nobold,noitalics,nounderscore] #{cpu_percentage} #[bg=colour248,fg=colour237] #h "

      set-window-option -g window-status-current-format "#[bg=colour214,fg=colour237,nobold,noitalics,nounderscore]#[bg=colour214,fg=colour239] #I #[bg=colour214,fg=colour239,bold] #W#{?window_zoomed_flag,*Z,} #[bg=colour237,fg=colour214,nobold,noitalics,nounderscore]"
      set-window-option -g window-status-format "#[bg=colour239,fg=colour237,noitalics]#[bg=colour239,fg=colour223] #I #[bg=colour239,fg=colour223] #W #[bg=colour237,fg=colour239,noitalics]"
    '';
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

      # Regenerate completion dump if it's older than 24 hours
      if [[ -n "$zcompdump"(#qN.mh+24) ]]; then
        compinit -d "$zcompdump"
      else
        compinit -C -d "$zcompdump"
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
    };

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

        # API Keys - managed by agenix
        source ~/.secrets/api-keys 2>/dev/null
      ''
    ];

    autosuggestion.enable = true;
    syntaxHighlighting.enable = true;
  };

  # ============================================================================
  # Nix Configuration
  # ============================================================================
  nix.package = pkgs.nix;
  nix.settings.experimental-features = [ "nix-command" "flakes" ];

  # ============================================================================
  # Launchd Agents (macOS scheduled tasks)
  # ============================================================================
  launchd.agents.home-manager-auto-update = lib.mkIf pkgs.stdenv.isDarwin {
    enable = true;
    config = {
      Label = "com.home-manager.auto-update";
      ProgramArguments = [
        "/bin/sh"
        "-c"
        ''
          export PATH="$HOME/.nix-profile/bin:/nix/var/nix/profiles/default/bin:$PATH"
          cd ~/.config/home-manager && \
          nix flake update 2>&1 | tee /tmp/home-manager-update.log && \
          home-manager switch --flake . 2>&1 | tee -a /tmp/home-manager-update.log
        ''
      ];
      StartCalendarInterval = [
        {
          Hour = 9;
          Minute = 0;
        }
      ];
      StandardOutPath = "/tmp/home-manager-auto-update.out.log";
      StandardErrorPath = "/tmp/home-manager-auto-update.err.log";
    };
  };

  # ============================================================================
  # Session Variables (available to all programs)
  # ============================================================================
  home.sessionVariables = {
    EDITOR = "nvim";
    LC_CTYPE = "en_US.UTF-8";
  } // lib.optionalAttrs pkgs.stdenv.isLinux {
    DOCKER_HOST = "unix:///run/user/1000/podman/podman.sock";
  };

  home.sessionPath = [
    "$HOME/.local/bin"
    "$HOME/.cargo/bin"
    "$HOME/go/bin"
  ];
}
