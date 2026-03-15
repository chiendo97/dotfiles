#!/usr/bin/env bash
input=$(cat)

cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // empty')
model=$(echo "$input" | jq -r '.model.display_name // empty')
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')

# Shorten home directory to ~
home="$HOME"
cwd="${cwd/#$home/\~}"

# Git branch (skip optional locks)
git_branch=""
if git -C "${cwd/#\~/$HOME}" --no-optional-locks rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git_branch=$(git -C "${cwd/#\~/$HOME}" --no-optional-locks symbolic-ref --short HEAD 2>/dev/null)
fi

# Build output using unicode symbols for visual distinction
parts=()

# Directory — folder emoji
parts+=("📁 ${cwd}")

# Git branch — branch symbol
if [ -n "$git_branch" ]; then
  parts+=("⎇ ${git_branch}")
fi

# Model — robot emoji
if [ -n "$model" ]; then
  parts+=("🤖 ${model}")
fi

# Context usage — meter emoji, warning above 80%
if [ -n "$used_pct" ]; then
  printf_pct=$(printf "%.0f" "$used_pct" 2>/dev/null || echo "$used_pct")
  if [ "${printf_pct}" -ge 80 ] 2>/dev/null; then
    parts+=("⚠️  ctx ${printf_pct}%")
  else
    parts+=("◈ ctx ${printf_pct}%")
  fi
fi

# Join parts with a unicode separator
separator=" · "
output=""
for part in "${parts[@]}"; do
  if [ -z "$output" ]; then
    output="${part}"
  else
    output="${output}${separator}${part}"
  fi
done

echo "$output"
