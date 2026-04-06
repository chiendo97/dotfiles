#!/usr/bin/env bash
# Claude Code SessionEnd hook — summarize session work into daily zk journal
# Forks heavy work (claude -p) into background so it survives Ctrl+C

JOURNAL_DIR="$HOME/Source/selfhost/zk/journal"
LOG_FILE="$HOME/.claude/hooks/journal-action-items.log"
LOCK_FILE="/tmp/journal-action-items.lock"

# Read hook JSON from stdin immediately (before session dies)
INPUT=$(cat)

# Fork everything else into a detached background process
(
  set -euo pipefail

  log() {
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $*" >> "$LOG_FILE" 2>/dev/null
  }

  TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty')
  CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

  # Exit silently if no transcript or no cwd
  if [ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ] || [ -z "$CWD" ]; then
    exit 0
  fi

  # Extract project name from git repo root, fallback to cwd basename
  if git -C "$CWD" rev-parse --show-toplevel &>/dev/null; then
    PROJECT=$(basename "$(git -C "$CWD" rev-parse --show-toplevel)")
  else
    PROJECT=$(basename "$CWD")
  fi

  # Grab recent commits (last 8 hours) for context
  GIT_LOG=""
  if git -C "$CWD" rev-parse --is-inside-work-tree &>/dev/null; then
    GIT_LOG=$(git -C "$CWD" log --oneline --since="8 hours ago" 2>/dev/null || true)
  fi

  # Extract last ~50 messages from transcript (it's JSONL)
  TRANSCRIPT_TAIL=$(tail -50 "$TRANSCRIPT")

  # Build prompt for claude -p
  PROMPT="You are summarizing a Claude Code session for a daily work journal.

Project: ${PROJECT}
Working directory: ${CWD}
Recent commits:
${GIT_LOG}

Transcript (last 50 messages):
${TRANSCRIPT_TAIL}

Rules:
- Output ONLY markdown bullets, one per meaningful outcome. No preamble, no explanation.
- Each bullet starts with \`- [[${PROJECT}]] — \`
- Summarize at a high level: \"reviewed MR !24\", \"fixed auth bug in middleware\", \"added retry logic to ingestion pipeline\"
- Skip trivial actions (reading files, exploring code without outcome, failed attempts that led nowhere)
- If nothing meaningful was accomplished, output nothing (empty response)
- Combine related work into single bullets rather than listing every small step
- Max 5 bullets per session"

  # Call claude -p with haiku for speed and cost
  SUMMARY=$(echo "$PROMPT" | claude -p --model haiku --no-session-persistence 2>/dev/null) || {
    log "ERROR: claude -p failed for project=$PROJECT cwd=$CWD"
    exit 0
  }

  # Exit if no meaningful work
  SUMMARY=$(echo "$SUMMARY" | sed '/^$/d')
  if [ -z "$SUMMARY" ]; then
    exit 0
  fi

  TODAY=$(date +"%Y-%m-%d")
  JOURNAL_FILE="${JOURNAL_DIR}/${TODAY}.md"

  # Use flock to prevent concurrent writes
  exec 9>"$LOCK_FILE"
  flock -w 10 9 || {
    log "ERROR: could not acquire lock for project=$PROJECT"
    exit 0
  }

  if [ ! -f "$JOURNAL_FILE" ]; then
    # Case 1: No journal file — create with template
    cat > "$JOURNAL_FILE" <<TEMPLATE
---
title: ${TODAY}
tags: [journal]
---

# ${TODAY}

## Tasks

- [ ]

## Notes

## Claude Code

${SUMMARY}
TEMPLATE

  elif ! grep -q '^## Claude Code' "$JOURNAL_FILE"; then
    # Case 2: Journal exists, no Claude Code section — append at end
    printf '\n## Claude Code\n\n%s\n' "$SUMMARY" >> "$JOURNAL_FILE"

  else
    # Case 3: Claude Code section exists — insert bullets after last bullet in section
    SECTION_START=$(grep -n '^## Claude Code' "$JOURNAL_FILE" | head -1 | cut -d: -f1)

    # Find the next ## heading after Claude Code section
    NEXT_SECTION=$(tail -n +"$((SECTION_START + 1))" "$JOURNAL_FILE" | grep -n '^## ' | head -1 | cut -d: -f1 || true)

    if [ -n "$NEXT_SECTION" ]; then
      # Insert before the next section
      INSERT_LINE=$((SECTION_START + NEXT_SECTION - 1))
      # Use head/tail to splice the file (robust for multi-line SUMMARY)
      TMPFILE=$(mktemp)
      trap 'rm -f "$TMPFILE"' EXIT
      head -n "$((INSERT_LINE - 1))" "$JOURNAL_FILE" > "$TMPFILE"
      printf '%s\n' "$SUMMARY" >> "$TMPFILE"
      tail -n +"$INSERT_LINE" "$JOURNAL_FILE" >> "$TMPFILE"
      mv "$TMPFILE" "$JOURNAL_FILE"
    else
      # No next section — append at end of file
      printf '%s\n' "$SUMMARY" >> "$JOURNAL_FILE"
    fi
  fi

  # Release lock
  exec 9>&-

  log "OK: appended summary for project=$PROJECT to $JOURNAL_FILE"
) </dev/null &>/dev/null & disown

exit 0
