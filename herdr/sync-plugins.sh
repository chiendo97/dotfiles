#!/bin/sh
# Sync herdr plugins from herdr/plugins.list (declarative).
# Lines: owner/repo[/subdir] [--ref REF]; '#' comments and blanks ignored.
# Skips installs already at the pinned commit; run install without --ref
# (or delete the pin) to update a plugin.
set -eu

list="${1:-herdr/plugins.list}"

while IFS= read -r spec || [ -n "$spec" ]; do
  case "$spec" in
    ""|\#*) continue ;;
  esac
  ref=""
  case "$spec" in
    *" --ref "*) ref="${spec##*--ref }"; repo="${spec%%--ref*}" ;;
    *) repo="$spec" ;;
  esac
  repo="${repo%% *}"
  ref="${ref%% *}"
  if [ -n "$ref" ] && herdr plugin list 2>/dev/null | grep -q "github:${repo}@${ref}"; then
    echo "herdr plugin ${repo} @ ${ref} already installed, skipping"
  else
    herdr plugin install $spec --yes
  fi
done < "$list"