---
name: discord
description: >
  Interact with Discord channels, threads, and DMs via CLI. Use this skill whenever you need to
  send messages, read messages, send files, manage threads, list channels, or react to messages
  in Discord. Even if the user doesn't mention "discord" by name — if they want to communicate
  via chat, notify someone, or check messages, use this skill.
---

# discord — Discord Bot CLI

A standalone Python CLI that talks to the Discord REST API using only stdlib (`urllib`).
Run it with `uv` — no dependencies to install.

**Requires environment variables:**
- `DISCORD_TOKEN` — your bot token
- `DISCORD_GUILD_ID` — default guild (server) ID

## Quick Reference

| Subcommand | Description |
|------------|-------------|
| `send` | Send a message to a channel, thread, or DM |
| `edit` | Edit an existing message |
| `get` | Get recent messages from a channel |
| `channels` | List all channels in a guild |
| `thread` | Create a new thread |
| `react` | React to a message with an emoji |
| `send-file` | Upload a file to a channel, thread, or DM |

## Usage

All commands are run via:

```bash
uv run /home/cle/.claude/skills/discord/discord_cli.py <subcommand> [options]
```

---

### send — Send a message

Send to a channel, thread, or user DM. Optionally reply to an existing message.

```bash
# Send to a channel
uv run /home/cle/.claude/skills/discord/discord_cli.py send --channel-id 123456 "Hello, world!"

# Send a DM to a user
uv run /home/cle/.claude/skills/discord/discord_cli.py send --user-id 789012 "Hey there!"

# Send to a thread
uv run /home/cle/.claude/skills/discord/discord_cli.py send --thread-id 345678 "Thread reply"

# Reply to a specific message
uv run /home/cle/.claude/skills/discord/discord_cli.py send --channel-id 123456 --reply-to 999888 "Replying to you"
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--channel-id` | One of three | Target channel ID |
| `--thread-id` | One of three | Target thread ID |
| `--user-id` | One of three | Target user ID (creates DM) |
| `--reply-to` | No | Message ID to reply to |
| `message` | Yes | The message text (positional arg) |

---

### edit — Edit a message

```bash
uv run /home/cle/.claude/skills/discord/discord_cli.py edit --channel-id 123456 --message-id 999888 "Updated content"
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--channel-id` | Yes | Channel containing the message |
| `--message-id` | Yes | ID of the message to edit |
| `content` | Yes | New message content (positional arg) |

---

### get — Get recent messages

Retrieves messages in chronological order (oldest first).

```bash
# Get last 20 messages (default)
uv run /home/cle/.claude/skills/discord/discord_cli.py get --channel-id 123456

# Get last 50 messages
uv run /home/cle/.claude/skills/discord/discord_cli.py get --channel-id 123456 --limit 50
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--channel-id` | Yes | Channel to read from |
| `--limit` | No | Number of messages to fetch (default: 20, max: 100) |

---

### channels — List guild channels

Lists all channels grouped by category.

```bash
# Use default guild from DISCORD_GUILD_ID
uv run /home/cle/.claude/skills/discord/discord_cli.py channels

# Specify a guild
uv run /home/cle/.claude/skills/discord/discord_cli.py channels --guild-id 111222333
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--guild-id` | No | Guild ID (defaults to `DISCORD_GUILD_ID` env var) |

---

### thread — Create a thread

Create a standalone thread or a thread from an existing message.

```bash
# Standalone thread in a channel
uv run /home/cle/.claude/skills/discord/discord_cli.py thread --channel-id 123456 --name "Discussion Topic"

# Thread from a message
uv run /home/cle/.claude/skills/discord/discord_cli.py thread --channel-id 123456 --name "Follow-up" --message-id 999888
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--channel-id` | Yes | Parent channel ID |
| `--name` | Yes | Thread name |
| `--message-id` | No | Message to create thread from |

---

### react — React to a message

```bash
uv run /home/cle/.claude/skills/discord/discord_cli.py react --channel-id 123456 --message-id 999888 --emoji thumbsup
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--channel-id` | Yes | Channel containing the message |
| `--message-id` | Yes | Message to react to |
| `--emoji` | Yes | Emoji name without colons (e.g. `thumbsup`, `fire`, `white_check_mark`) |

---

### send-file — Upload a file

Send a file to a channel, thread, or DM with an optional message.

```bash
# File to a channel
uv run /home/cle/.claude/skills/discord/discord_cli.py send-file --channel-id 123456 --file ./report.pdf

# File with a message
uv run /home/cle/.claude/skills/discord/discord_cli.py send-file --channel-id 123456 --file ./image.png --message "Check this out"

# File to a DM
uv run /home/cle/.claude/skills/discord/discord_cli.py send-file --user-id 789012 --file ./data.csv

# File to a thread
uv run /home/cle/.claude/skills/discord/discord_cli.py send-file --thread-id 345678 --file ./log.txt
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--channel-id` | One of three | Target channel ID |
| `--thread-id` | One of three | Target thread ID |
| `--user-id` | One of three | Target user ID (creates DM) |
| `--file` | Yes | Path to file to upload |
| `--message` | No | Optional text message with the file |

---

## Output Format

All commands print human-readable text with embedded IDs for programmatic use:

```
Sent (msg:123456789) to channel:987654321
  Hello, world!
```

Message IDs are always in the format `msg:ID` and channel IDs as `channel:ID` so they can be parsed if needed.

## Error Handling

- Missing environment variables produce a clear error and exit code 1
- HTTP errors show the Discord API error message
- Network errors are reported with the underlying reason
- Missing files for `send-file` are caught before making API calls

## DM Behavior

When using `--user-id`, the CLI first creates (or retrieves) a DM channel with that user via `POST /users/@me/channels`, then sends the message to that channel. This is how the Discord API requires DMs to work.
