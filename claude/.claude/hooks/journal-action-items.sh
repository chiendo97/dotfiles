#!/usr/bin/env bash
# SessionEnd hook — summarize session work into daily zk journal
set -euo pipefail

JOURNAL_DIR="$HOME/Source/selfhost/zk/journal"
LOG_FILE="$HOME/.claude/hooks/journal-action-items.log"
LOCK_FILE="/tmp/journal-action-items.lock"

log() {
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] $*" >> "$LOG_FILE" 2>/dev/null
}

INPUT=$(cat)

TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

if [ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ] || [ -z "$CWD" ]; then
  exit 0
fi

if git -C "$CWD" rev-parse --show-toplevel &>/dev/null; then
  PROJECT=$(basename "$(git -C "$CWD" rev-parse --show-toplevel)")
else
  PROJECT=$(basename "$CWD")
fi

GIT_LOG=""
if git -C "$CWD" rev-parse --is-inside-work-tree &>/dev/null; then
  GIT_LOG=$(git -C "$CWD" log --oneline --since="8 hours ago" 2>/dev/null || true)
fi

TRANSCRIPT_TAIL=$(tail -50 "$TRANSCRIPT")

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

SUMMARY=$(echo "$PROMPT" | claude -p --model haiku --no-session-persistence 2>/dev/null) || {
  log "ERROR: claude -p failed for project=$PROJECT cwd=$CWD"
  exit 0
}

SUMMARY=$(echo "$SUMMARY" | sed '/^$/d')
if [ -z "$SUMMARY" ]; then
  exit 0
fi

TODAY=$(date +"%Y-%m-%d")
JOURNAL_FILE="${JOURNAL_DIR}/${TODAY}.md"

exec 9>"$LOCK_FILE"
flock -w 10 9 || {
  log "ERROR: could not acquire lock for project=$PROJECT"
  exit 0
}

if [ ! -f "$JOURNAL_FILE" ]; then
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
  printf '\n## Claude Code\n\n%s\n' "$SUMMARY" >> "$JOURNAL_FILE"

else
  printf '%s\n' "$SUMMARY" >> "$JOURNAL_FILE"
fi

exec 9>&-

log "OK: appended summary for project=$PROJECT to $JOURNAL_FILE"
