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
    (import ./packages/ai.nix { inherit pkgs; }) ++
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

  home.activation.glabConfig = lib.hm.dag.entryAfter [ "writeBoundary" ] ''
    install -Dm600 /dev/null "${config.xdg.configHome}/glab-cli/config.yml"
    cat > "${config.xdg.configHome}/glab-cli/config.yml" << 'GLABEOF'
    git_protocol: ssh
    glamour_style: dark
    check_update: false
    host: git.urieljsc.com
    no_prompt: false
    hosts:
      git.urieljsc.com:
        api_host: git.urieljsc.com
        git_protocol: ssh
        api_protocol: https
        user: cle
        ssh_host: git.urieljsc.com
    GLABEOF
    chmod 600 "${config.xdg.configHome}/glab-cli/config.yml"
  '';

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

    matchBlocks = {
      "*" = {
        addKeysToAgent = "yes";
      };

      "cle-home-server" = {
        hostname = "100.118.125.39";
        user = "cle";
      };

      "vng-gateway-01" = {
        hostname = "42.1.126.5";
        port = 234;
        user = "cle";
        identityFile = "~/.ssh/id_ed25519_vng_gateway_01";
      };

      "cle-homic" = {
        hostname = "100.83.74.104";
        user = "root";
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

  programs.tmux = {
    enable = true;
    mouse = true;
    keyMode = "vi";
    escapeTime = 0;
    baseIndex = 1;
    prefix = "C-Space";
    terminal = "tmux-256color";
    focusEvents = true;
    historyLimit = 50000;
    sensibleOnTop = true;

    plugins = with pkgs.tmuxPlugins; [
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
      set -as terminal-features ',tmux-256color:RGB:clipboard'
      set -g renumber-windows on
      set -g set-titles on
      set -g set-titles-string "#{session_name}"
      set-option -s set-clipboard on
      set -g allow-passthrough on
      set -g display-panes-time 2000

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
      bind-key -r H resize-pane -L 5
      bind-key -r J resize-pane -D 5
      bind-key -r K resize-pane -U 5
      bind-key -r L resize-pane -R 5

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

      # Window picker with fzf
      bind w run-shell -b "tmux list-windows -F '##I: ##W' | fzf-tmux -h --layout=reverse | cut -d: -f1 | xargs tmux select-window -t"

      # New window keeps current path
      bind c new-window -c '#{pane_current_path}'

      # Quick kill pane without confirmation
      bind X kill-pane

      # Popup scratch terminal
      bind t display-popup -E -w 80% -h 80% -d '#{pane_current_path}'

      # Swap windows
      bind-key -n C-S-Left swap-window -d -t -1
      bind-key -n C-S-Right swap-window -d -t +1

      # === Theme: Gruvbox Dark ===
      set-option -g status "on"
      set-option -g status-style bg=colour237,fg=colour223
      set-window-option -g window-status-style bg=colour214,fg=colour237
      set-window-option -g window-status-activity-style bg=colour237,fg=colour248
      set-window-option -g window-status-current-style bg=colour142,fg=colour237
      set-option -g pane-border-lines double
      set-option -g pane-border-indicators both
      set-option -g pane-border-status bottom
      set-option -g pane-border-format "#[bold] #{pane_index}: #{pane_current_command} #[nobold]#{?pane_active,, │ #{pane_current_path}}"
      set-option -g pane-active-border-style fg=colour108
      set-option -g pane-border-style fg=colour239

      # Dim inactive panes (Gruvbox bg0_h/bg0_s)
      set-option -g window-style 'fg=colour246,bg=colour234'
      set-option -g window-active-style 'fg=colour223,bg=colour236'
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
      set-option -g status-right "#{prefix_highlight}#[bg=colour237,fg=colour239,nobold,noitalics,nounderscore]#[bg=colour239,fg=colour246] %Y-%m-%d  %H:%M #[bg=colour239,fg=colour248,nobold,noitalics,nounderscore]#[bg=colour248,fg=colour237] #h "

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

      # Claude
      _claude = "claude --dangerously-skip-permissions";

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
    ZK_NOTEBOOK_DIR = "${config.home.homeDirectory}/Source/selfhost/zk";
    CLAUDE_CODE_NO_FLICKER = "1";
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
}
