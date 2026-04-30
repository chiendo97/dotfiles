---
name: discord-thread-renamer
description: Rename Discord threads to follow a consistent `[category] — topic` convention. Use this skill whenever the user wants to clean up thread names, organize Discord threads, rename threads in bulk, or improve thread discoverability in any channel. Also trigger when the user mentions messy thread names, truncated thread titles, or wants to make threads scannable.
---

# Discord Thread Renamer

Rename Discord threads so anyone can understand what a thread is about without opening it. Uses a `[category] — topic` naming convention with auto-detection of PR/MR links.

## Dependencies

This skill uses the Discord CLI at `/home/cle/.claude/skills/discord/discord_cli.py`. Invoke it via the `discord` skill for command reference.

## Naming Convention

### Format

```
[category] — topic
```

- **category**: A short lowercase keyword describing the domain. When a thread is a PR/MR review, embed the number: `[review-pr-332]` or `[review-mr-15]`.
- **topic**: A concise description of what the thread is about. Enough to understand without opening. Not a full sentence — think search index entry.

### Examples

```
[infra] — RDS storage & JE table
[pipeline] — Prefect flow run dev rebuild
[review-pr-332] — finance settlement posted date
[migration] — Airbyte to dp-sdk
[client] — fx-rate & shop-name in export
[data] — ledger re-call t1-t3
[process] — enforce threads in #genbooks
```

### Category Selection

Categories are **not** a fixed list — they emerge from the channel's domain. Common patterns:

| Pattern | When to use |
|---------|------------|
| `infra` | Servers, databases, deployments, storage |
| `data` | Backfill, data pulls, exports, transformations |
| `pipeline` | Prefect/Airflow flows, pipeline failures |
| `api` | API changes, endpoint bugs |
| `frontend` | FE issues, UI bugs |
| `migration` | Schema changes, platform migrations |
| `review-pr-N` | GitHub PR review (auto-detect from links) |
| `review-mr-N` | GitLab MR review (auto-detect from links) |
| `incident` | Outages, security issues, creds exposed |
| `client` | Client-reported issues, client requests |
| `process` | Team rules, conventions, workflow |

When a thread doesn't fit existing categories, invent a short descriptive one. The goal is consistency within a channel, not a global taxonomy.

## Workflow

### 1. List threads

List active threads, optionally filtered by channel:

```bash
uv run /home/cle/.claude/skills/discord/discord_cli.py threads --channel-id <channel-id>
```

If the user doesn't specify a channel, list all threads and ask which channel to focus on.

### 2. Identify threads needing rename

Threads with bad names typically have:
- Truncated `@mention` prefixes (e.g. `@User1 @User2 please take a look`)
- Raw URLs or link fragments
- Emojis only or emoji-heavy names
- Vague single words (`fixing`, `update`, `test`)
- Names that don't describe the topic

Skip threads that already follow `[category] — topic` format. All other threads should be renamed for consistency — even ones with somewhat descriptive names like `MR !21 — fix: handle missing ticket ID...` should be reformatted to `[review-mr-21] — fix missing ticket ID in notion-sync`.

### 3. Read thread content

For each thread needing rename, read messages to understand context:

```bash
uv run /home/cle/.claude/skills/discord/discord_cli.py get --channel-id <thread-id> --limit 10
```

The `get` command auto-fetches the thread starter message from the parent channel. This is critical because many threads are created from a channel message, and the starter often contains the full context (PR links, descriptions) while the thread replies may only have "approved" or reactions.

### 4. Auto-detect PR/MR links

When reading thread content, scan for:
- `github.com/.../pull/<number>` → use `[review-pr-<number>]`
- `gitlab.com/.../merge_requests/<number>` or `git.<domain>/.../merge_requests/<number>` → use `[review-mr-<number>]`

If a PR/MR link is found and the thread is primarily a review/approval thread, use the review category with the embedded number.

### 5. Propose names and get approval

Present a table of proposed renames to the user:

```
| # | Current Name | Proposed Name |
|---|---|---|
| 1 | @User please look at... | [review-pr-332] — finance settlement posted date |
| 2 | fixing stuff | [api] — inventory date filter bug |
```

Wait for user approval before renaming. The user may want to adjust names or skip some threads.

### 6. Rename in bulk

After approval, rename all threads in parallel:

```bash
uv run /home/cle/.claude/skills/discord/discord_cli.py rename --thread-id <id> --name "<new name>"
```

## Guidelines

- **Topic should be self-explanatory.** Someone scanning the thread list should understand what happened without opening the thread.
- **Keep names concise.** Discord truncates long thread names. Aim for under 60 characters total.
- **Don't include @mentions in the new name.** The original name often starts with mentions — strip them.
- **Preserve useful context.** If the original name has a good keyword (like a ticket number), keep it.
- **When content is just "approved" with no other context**, and you can't determine what was being reviewed from the starter message, use a generic `[review] — approval (date)` format with the thread creation date.
- **Batch renames in parallel** using multiple tool calls in one message for efficiency.
