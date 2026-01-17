{ config, lib, pkgs, neovim-nightly-overlay, homeDirectory, username, ... }:

{
  home.username = username;
  home.homeDirectory = homeDirectory;
  home.stateVersion = "25.11";

  # ============================================================================
  # Agenix secrets
  # ============================================================================
  age.identityPaths = [ "${config.home.homeDirectory}/.ssh/id_ed25519_agenix" ];

  age.secrets.api-keys = {
    file = ./secrets/api-keys.age;
    path = "${config.home.homeDirectory}/.secrets/api-keys";
  };

  # SSH private keys
  age.secrets.aws_bastion_rsa = {
    file = ./secrets/aws_bastion_rsa.age;
    path = "${config.home.homeDirectory}/.ssh/aws_bastion_rsa";
    mode = "600";
  };
  age.secrets.cle_viettel_idc = {
    file = ./secrets/cle_viettel_idc.age;
    path = "${config.home.homeDirectory}/.ssh/cle_viettel_idc";
    mode = "600";
  };
  age.secrets.cle_vpn = {
    file = ./secrets/cle_vpn.age;
    path = "${config.home.homeDirectory}/.ssh/cle_vpn";
    mode = "600";
  };
  age.secrets.github_key = {
    file = ./secrets/github_key.age;
    path = "${config.home.homeDirectory}/.ssh/github_key";
    mode = "600";
  };
  age.secrets.github_rsa = {
    file = ./secrets/github_rsa.age;
    path = "${config.home.homeDirectory}/.ssh/github_rsa";
    mode = "600";
  };
  age.secrets.homic_olympus = {
    file = ./secrets/homic_olympus.age;
    path = "${config.home.homeDirectory}/.ssh/homic_olympus";
    mode = "600";
  };
  age.secrets.homic_rsa = {
    file = ./secrets/homic_rsa.age;
    path = "${config.home.homeDirectory}/.ssh/homic_rsa";
    mode = "600";
  };
  age.secrets.id_ed25519_github = {
    file = ./secrets/id_ed25519_github.age;
    path = "${config.home.homeDirectory}/.ssh/id_ed25519_github";
    mode = "600";
  };
  age.secrets.oracle = {
    file = ./secrets/oracle.age;
    path = "${config.home.homeDirectory}/.ssh/oracle";
    mode = "600";
  };
  age.secrets.uriel_rsa = {
    file = ./secrets/uriel_rsa.age;
    path = "${config.home.homeDirectory}/.ssh/uriel_rsa";
    mode = "600";
  };

  # ============================================================================
  # Packages (no Home Manager module available)
  # ============================================================================
  home.packages = with pkgs; [
    age        # for agenix secrets
    claude-code
    curl
    fd
    gnumake
    htop
    jq
    nodejs
    podman
    ripgrep
    rustup
    stow
    tree
    unzip
    uv
    wget
  ];

  # ============================================================================
  # Programs with Home Manager modules
  # ============================================================================
  programs.neovim = {
    enable = true;
    package = neovim-nightly-overlay.packages.${pkgs.system}.default;
  };

  programs.fzf = {
    enable = true;
    enableZshIntegration = true;
  };

  programs.zoxide = {
    enable = true;
    enableZshIntegration = true;
  };

  programs.go = {
    enable = true;
  };

  programs.eza = {
    enable = true;
  };

  programs.bat = {
    enable = true;
  };

  programs.ssh = {
    enable = true;
    enableDefaultConfig = false;

    includes = [
      "~/.orbstack/ssh/config"
    ];

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
        plugin = sensible;
        extraConfig = "";
      }
      {
        plugin = mkTmuxPlugin {
          pluginName = "tmux-buffer";
          version = "unstable";
          rtpFilePath = "buffex.tmux";
          src = pkgs.fetchFromGitHub {
            owner = "chiendo97";
            repo = "tmux-buffer";
            rev = "master";
            sha256 = "sha256-fqKYEbAXdgogLhTbuPl1ogHu/2jsyg4+oT82jxuKwlY=";
          };
        };
      }
    ];

    extraConfig = ''
      # === General ===
      set -g allow-rename off
      set -g detach-on-destroy off
      set -g pane-base-index 1
      set -ag terminal-overrides ",xterm-256color:RGB"
      set -as terminal-features ',xterm-256color:clipboard'
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
      set-option -g pane-active-border-style fg=colour250
      set-option -g pane-border-style fg=colour237
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

      set -g @plugin 'chiendo97/tmux-buffer'
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
      save = 10000;
      path = "${config.home.homeDirectory}/.zsh_history";
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
    };

    # Session variables
    sessionVariables = {
      EDITOR = "nvim";
      GO111MODULE = "auto";
      GOSUMDB = "off";
    };

    # Additional paths
    envExtra = ''
      export PATH="$HOME/.local/bin:$PATH"
      export PATH="$HOME/.cargo/bin:$PATH"
    '';

    # Zsh init content using lib.mkOrder for proper ordering
    initContent = lib.mkMerge [
      # Early init (source nix first)
      (lib.mkBefore ''
        # Source nix
        if [ -e "$HOME/.nix-profile/etc/profile.d/nix.sh" ]; then
          . "$HOME/.nix-profile/etc/profile.d/nix.sh"
        fi
      '')

      # Main init content
      ''
        # Emacs keybindings
        bindkey -e

        # Edit command line with ^g
        autoload -U edit-command-line
        zle -N edit-command-line
        bindkey '^g' edit-command-line

        # API Keys - managed by agenix
        source ~/.secrets/api-keys 2>/dev/null
      ''
    ];

    # Plugins
    plugins = [
      {
        name = "pure";
        src = pkgs.fetchFromGitHub {
          owner = "sindresorhus";
          repo = "pure";
          rev = "v1.23.0";
          sha256 = "sha256-BmQO4xqd/3QnpLUitD2obVxL0UulpboT8jGNEh4ri8k=";
        };
      }
      {
        name = "zsh-autosuggestions";
        src = pkgs.fetchFromGitHub {
          owner = "zsh-users";
          repo = "zsh-autosuggestions";
          rev = "v0.7.1";
          sha256 = "sha256-vpTyYq9ZgfgdDsWzjxVAE7FZH4MALMNZIFyEOBLm5Qo=";
        };
      }
    ];
  };

  # ============================================================================
  # Cachix Configuration for Claude Code
  # ============================================================================
  nix.package = pkgs.nix;
  nix.settings = {
    substituters = [ "https://claude-code.cachix.org" "https://cache.nixos.org" ];
    trusted-public-keys = [
      "cache.nixos.org-1:6NCHdD59X431o0gWypbMrAURkbJ16ZPMQFGspcDShjY="
      "claude-code.cachix.org-1:YeXf2aNu7UTX8Vwrze0za1WEDS+4DuI2kVeWEE4fsRk="
    ];
  };
  nix.extraOptions = ''
    experimental-features = nix-command flakes
  '';

  # ============================================================================
  # Session Variables (available to all programs)
  # ============================================================================
  home.sessionVariables = {
    EDITOR = "nvim";
  };

  home.sessionPath = [
    "$HOME/.local/bin"
    "$HOME/.cargo/bin"
    "$HOME/go/bin"
  ];
}
