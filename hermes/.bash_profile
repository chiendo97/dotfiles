# Bootstrap the Home Manager Zsh environment for interactive login shells.
# Non-interactive SSH commands, SCP, and SFTP remain under the account shell.
if [[ $- == *i* ]] && [[ -z "${BASH_EXECUTION_STRING:-}" ]] && [[ -x "$HOME/.nix-profile/bin/zsh" ]] && [[ -z "${ZSH_VERSION:-}" ]]; then
  export SHELL="$HOME/.nix-profile/bin/zsh"
  exec "$SHELL" -l
fi

# Preserve the normal login environment when Zsh is unavailable.
if [[ -f "$HOME/.profile" ]]; then
  . "$HOME/.profile"
fi
