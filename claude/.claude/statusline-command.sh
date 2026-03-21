#!/usr/bin/env bash
input=$(cat)

# Parse JSON fields
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // empty')
model=$(echo "$input" | jq -r '.model.display_name // empty')
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')
rate_pct=$(echo "$input" | jq -r '.rate_limits.used_percentage // empty')

# Shorten home directory to ~
cwd="${cwd/#$HOME/\~}"

# Git branch (skip optional locks)
git_branch=""
git_dir="${cwd/#\~/$HOME}"
if git -C "$git_dir" --no-optional-locks rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git_branch=$(git -C "$git_dir" --no-optional-locks symbolic-ref --short HEAD 2>/dev/null)
fi

# ANSI colors — chosen for visibility on both light and dark terminals
reset=$'\033[0m'
dim=$'\033[2m'
green=$'\033[32m'
yellow=$'\033[33m'
red=$'\033[31m'
cyan=$'\033[36m'
blue=$'\033[34m'

# Threshold color: green <60, yellow 60-79, red 80+
threshold_color() {
  local val=$1
  local n
  n=$(printf "%.0f" "$val" 2>/dev/null) || n=0
  if [ "$n" -ge 80 ] 2>/dev/null; then
    echo "$red"
  elif [ "$n" -ge 60 ] 2>/dev/null; then
    echo "$yellow"
  else
    echo "$green"
  fi
}

sep="${dim} · ${reset}"
parts=()

# 1. CWD — dim, truncated to last 30 chars
if [ -n "$cwd" ]; then
  if [ "${#cwd}" -gt 30 ]; then
    cwd="…${cwd: -29}"
  fi
  parts+=("${dim}${cwd}${reset}")
fi

# 2. Git branch — cyan (terminal convention)
if [ -n "$git_branch" ]; then
  parts+=("${cyan}⎇ ${git_branch}${reset}")
fi

# 3. Model
if [ -n "$model" ]; then
  parts+=("${blue}${model}${reset}")
fi

# 4. Context usage — percentage only, progressive color
if [ -n "$used_pct" ]; then
  pct=$(printf "%.0f" "$used_pct" 2>/dev/null || echo "?")
  clr=$(threshold_color "$used_pct")
  parts+=("${clr}${pct}%${reset}")
fi

# 5. Rate limit — progressive color
if [ -n "$rate_pct" ]; then
  rpct=$(printf "%.0f" "$rate_pct" 2>/dev/null || echo "?")
  rclr=$(threshold_color "$rate_pct")
  parts+=("${rclr}rate ${rpct}%${reset}")
fi

# Join parts with dimmed separator
output=""
for part in "${parts[@]}"; do
  if [ -z "$output" ]; then
    output="$part"
  else
    output="${output}${sep}${part}"
  fi
done

echo "$output"
