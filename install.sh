#!/usr/bin/env bash

DOTFILES="$(pwd)"
COLOR_GRAY="\033[1;38;5;243m"
COLOR_BLUE="\033[1;34m"
COLOR_GREEN="\033[1;32m"
COLOR_RED="\033[1;31m"
COLOR_PURPLE="\033[1;35m"
COLOR_YELLOW="\033[1;33m"
COLOR_NONE="\033[0m"

title() {
    echo -e "\n${COLOR_PURPLE}$1${COLOR_NONE}"
    echo -e "${COLOR_GRAY}==============================${COLOR_NONE}\n"
}

error() {
    echo -e "${COLOR_RED}Error: ${COLOR_NONE}$1"
    exit 1
}

warning() {
    echo -e "${COLOR_YELLOW}Warning: ${COLOR_NONE}$1"
}

info() {
    echo -e "${COLOR_BLUE}Info: ${COLOR_NONE}$1"
}

success() {
    echo -e "${COLOR_GREEN}$1${COLOR_NONE}"
}

sync_dotfiles() {
    title "Sync dotfiles"

    info "Tmux"
    cp -r "$DOTFILES/.tmux.conf" ~/.tmux.conf

    info "Alacritty"
    mkdir -p ~/.config/alacritty/
    cp -r "$DOTFILES/.config/alacritty/" ~/.config/alacritty/

    info "Neovim"
    mkdir -p ~/.config/nvim/
    cp -r "$DOTFILES/.config/nvim/" ~/.config/nvim/

    info "Shell"
    cp -r "$DOTFILES/.zshrc" ~/.zshrc

    info "Gitdotfiles"
    cp -r "$DOTFILES/.gitconfig" ~/.gitconfig
    cp -r "$DOTFILES/.gitignore_global" ~/.gitignore_global

    info "Zellij"
    rsync -av --delete "$DOTFILES/.config/zellij/" ~/.config/zellij/
}

sync_zsh_history() {
    title "Sync zsh history"

    title "Zsh history"
    cp -r "$DOTFILES/.zsh_history" ~/.zsh_history
}


update_dotfiles() {
    title "Update dotfiles"

    info "Tmux"
    cp ~/.tmux.conf "$DOTFILES/.tmux.conf"

    info "Alacritty"
    mkdir -p "$DOTFILES/.config/alacritty/"
    cp ~/.config/alacritty/* "$DOTFILES/.config/alacritty/"

    # info "Neovim"
    # mkdir -p "$DOTFILES/.config/nvim/"
    # rsync -av  --delete --exclude=.git ~/.config/nvim/ "$DOTFILES/.config/nvim/"

    info "Shell"
    cp ~/.tmux.conf "$DOTFILES/.tmux.conf"
    cp ~/.zshrc "$DOTFILES/.zshrc"

    info "Gitdotfiles"
    cp ~/.gitconfig "$DOTFILES/.gitconfig"
    cp ~/.gitignore_global "$DOTFILES/.gitignore_global"

    info "Zellij"
    rsync -av --delete ~/.config/zellij/ "$DOTFILES/.config/zellij/"
}

update_zsh_history() {
    title "Update zsh history"

    title "Zsh history"
    cp ~/.zsh_history "$DOTFILES/.zsh_history"
}

setup_terminfo() {
    title "Configuring terminfo"

    info "adding tmux.terminfo"
    tic -x "$DOTFILES/resources/tmux.terminfo"

    info "adding xterm-256color-italic.terminfo"
    tic -x "$DOTFILES/resources/xterm-256color-italic.terminfo"
}

case "$1" in
    terminfo)
        setup_terminfo
        ;;
    sync)
        sync_dotfiles
        ;;
    update)
        update_dotfiles
        ;;
    sync_zsh_history)
        sync_zsh_history
        ;;
    update_zsh_history)
        update_zsh_history
        ;;
    *)
        echo -e "Usage: $(basename "$0") {terminfo|sync|update|sync_zsh_history|update_zsh_history}\n"
        exit 1
        ;;
esac

echo -e
success "Done."
