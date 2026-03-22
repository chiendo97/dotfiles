#!/usr/bin/env bash
# Telegram notification hook for Claude Code
# Reads hook JSON from stdin, extracts context from transcript, sends formatted Telegram message

# Credentials from shell env (sourced via agenix api-keys in .zshrc)
BOT_TOKEN="${CLAUDE_TELEGRAM_BOT_TOKEN:?Missing CLAUDE_TELEGRAM_BOT_TOKEN}"
CHAT_ID="${CLAUDE_TELEGRAM_CHAT_ID:?Missing CLAUDE_TELEGRAM_CHAT_ID}"

LOG_FILE="$HOME/.claude/hooks/notification.log"

INPUT=$(cat)

NOTIFICATION_TYPE=$(echo "$INPUT" | jq -r '.notification_type // "unknown"')
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty')
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

# Pick emoji based on notification type
case "$NOTIFICATION_TYPE" in
  permission_prompt)  EMOJI="🔐"; LABEL="Permission needed" ;;
  idle_prompt)        EMOJI="💤"; LABEL="Waiting for input" ;;
  auth_success)       EMOJI="✅"; LABEL="Auth success" ;;
  elicitation_dialog) EMOJI="💬"; LABEL="Input requested" ;;
  *)                  EMOJI="🔔"; LABEL="Notification" ;;
esac

# Escape HTML special characters
escape_html() {
  local s="$1"
  s="${s//&/&amp;}"
  s="${s//</&lt;}"
  s="${s//>/&gt;}"
  echo "$s"
}

# Extract last assistant text (final paragraph) and last tool call from transcript
ASSISTANT_TEXT=""
DETAIL=""
if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
  # Get last assistant text block — extract final paragraph, truncate to 500 chars
  ASSISTANT_TEXT=$(tail -30 "$TRANSCRIPT" \
    | jq -r 'select(.type == "assistant") | .message.content[]
      | select(.type == "text") | .text' 2>/dev/null \
    | tail -1 \
    | awk 'BEGIN{RS="\n\n"; last=""} {last=$0} END{print last}' \
    | cut -c1-500)

  # Get the last tool_use entry
  LAST_TOOL=$(tail -30 "$TRANSCRIPT" \
    | jq -r 'select(.message.content != null) | .message.content[]
      | select(.type == "tool_use")' 2>/dev/null \
    | jq -s '.[-1]' 2>/dev/null)

  if [ -n "$LAST_TOOL" ] && [ "$LAST_TOOL" != "null" ]; then
    TOOL_NAME=$(echo "$LAST_TOOL" | jq -r '.name // empty')

    case "$TOOL_NAME" in
      Bash)
        CMD=$(echo "$LAST_TOOL" | jq -r '.input.command // empty' | cut -c1-200)
        [ -n "$CMD" ] && DETAIL="▶ Run: <code>$(escape_html "$CMD")</code>"
        ;;
      Edit|Write|Read)
        FILE=$(echo "$LAST_TOOL" | jq -r '.input.file_path // empty')
        [ -n "$FILE" ] && DETAIL="▶ ${TOOL_NAME}: <code>$(escape_html "$(basename "$FILE")")</code>"
        ;;
      Agent)
        DESC=$(echo "$LAST_TOOL" | jq -r '.input.description // .input.prompt // empty' | cut -c1-200)
        [ -n "$DESC" ] && DETAIL="▶ Agent: $(escape_html "$DESC")"
        ;;
      AskUserQuestion)
        Q=$(echo "$LAST_TOOL" | jq -r '.input.questions[0].question // empty' | cut -c1-200)
        [ -n "$Q" ] && DETAIL="❓ $(escape_html "$Q")"
        ;;
      *)
        DETAIL="▶ Tool: <code>$(escape_html "$TOOL_NAME")</code>"
        ;;
    esac
  fi
fi

# Build message
PROJECT="${CWD:+$(basename "$CWD")}"

PANE_ID="${TMUX_PANE:-}"

TEXT="${EMOJI} <b>${LABEL}</b>"
[ -n "$PROJECT" ] && TEXT="${TEXT}  ·  <code>$(escape_html "$PROJECT")</code>"
[ -n "$PANE_ID" ] && TEXT="${TEXT}  ·  <code>$(escape_html "$PANE_ID")</code>"

# Add assistant reasoning (the "why")
if [ -n "$ASSISTANT_TEXT" ]; then
  TEXT="${TEXT}

$(escape_html "$ASSISTANT_TEXT")"
fi

# Add action detail (the "what")
if [ -n "$DETAIL" ]; then
  TEXT="${TEXT}

${DETAIL}"
fi

# Fallback if we got neither
if [ -z "$ASSISTANT_TEXT" ] && [ -z "$DETAIL" ]; then
  TEXT="${TEXT}
Claude Code needs your attention"
fi

# Log to file
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
jq -n -c \
  --arg ts "$TS" \
  --arg type "$NOTIFICATION_TYPE" \
  --arg project "$PROJECT" \
  --arg detail "$DETAIL" \
  --arg assistant_text "$ASSISTANT_TEXT" \
  '{ts: $ts, type: $type, project: $project, detail: $detail, assistant_text: $assistant_text}' \
  >> "$LOG_FILE" 2>/dev/null

curl -s --connect-timeout 5 --max-time 10 \
  -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  --data-urlencode "chat_id=$CHAT_ID" \
  --data-urlencode "parse_mode=HTML" \
  --data-urlencode "text=$TEXT" > /dev/null 2>&1

exit 0
