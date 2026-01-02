# {{{ === ALIAS
alias l="eza"
alias t="tree --gitignore"
alias c='clear'
alias v='vim'  # quick opening files with vim
alias n='nvim' # quick opening files with vim

alias gi='git'
alias tx='tmux'
alias nv='nvim'
alias gf='git fetch --all'
alias gd='git diff'
alias gb='git branch'
alias gs='git status'
alias gl='git log'
alias ll='eza -l'

alias cpwd="\033Ptmux;\033\033]52;c;$(pwd | tr -d '\n' | base64)\a\033\\" # Copy pwd to clipboard

# go alias
alias pp='go tool pprof'
alias vendor='go mod vendor'
alias tidy='go mod tidy'
# }}}

# {{{ === PATH
export PATH="$HOME/.local/bin:$PATH"
export PATH="$HOME/.cargo/bin:$PATH"
# }}}

# {{{ === SETTING
# for pure zsh
if [[ ! -d $HOME/.zsh/pure ]]; then
  git clone https://github.com/sindresorhus/pure.git $HOME/.zsh/pure
fi
fpath+=($HOME/.zsh/pure)

# for docker autocompletion
# fpath+=($HOME/.docker/completions)

# Set up the prompt
autoload -U promptinit
promptinit
prompt pure

setopt histignorealldups sharehistory

# Use emacs keybindings even if our EDITOR is set to vi
bindkey -e

# Keep 1000 lines of history within the shell and save it to ~/.zsh_history:
HISTSIZE=1000
SAVEHIST=1000
HISTFILE=~/.zsh_history

# Use modern completion system
autoload -Uz compinit
compinit

export EDITOR='nvim'
# }}}

# {{{ === MAPPING KEY
autoload -U edit-command-line
zle -N edit-command-line
bindkey '^g' edit-command-line
# }}}

# {{{ === GO DEV
export GOPATH=$HOME/go
export GOBIN=$GOPATH/bin
export GO111MODULE=auto
export GOSUMDB=off
export PATH=$GOPATH/bin:$PATH
# }}}

# {{{ === FASD INIT ===
if ! command -v zoxide &>/dev/null; then
  curl -sS https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh | bash
fi

eval "$(zoxide init zsh)"
# }}}

if [ ! -d ~/.zsh/zsh-autosuggestions ]; then
  git clone https://github.com/zsh-users/zsh-autosuggestions ~/.zsh/zsh-autosuggestions
fi

source ~/.zsh/zsh-autosuggestions/zsh-autosuggestions.zsh

if [ ! -d ~/.fzf ]; then
  git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
  ~/.fzf/install
fi

# fzf init setup
[ -f ~/.fzf.zsh ] && source ~/.fzf.zsh

lazy_load_nvm() {
  unset -f npm node nvm
  export NVM_DIR=~/.nvm
  [[ -s "$NVM_DIR/nvm.sh" ]] && source "$NVM_DIR/nvm.sh"
  [ -s "$NVM_DIR/bash_completion" ] && source "$NVM_DIR/bash_completion"
}

npm() {
  lazy_load_nvm
  npm $@
}

node() {
  lazy_load_nvm
  node $@
}

nvm() {
  lazy_load_nvm
  nvm $@
}

# zprof
