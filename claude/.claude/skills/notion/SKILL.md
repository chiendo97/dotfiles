---
name: notion
description: >
  Manage Notion tickets and epics via CLI. Use this skill whenever you need to create tickets,
  search tasks, update ticket status/priority/assignee, list epics, or discover workspace users.
  Even if the user doesn't mention "notion" by name — if they want to track work, manage tasks,
  check sprint status, or update ticket progress, use this skill.
---

# Notion CLI

Standalone Python CLI for Notion ticket/epic operations. Runs via `uv` with no project dependencies.

## Environment

Requires `NOTION_TOKEN` environment variable (Notion integration token).

## Config

Reads from `./config/notion.yaml` or `~/Source/claude-boy/config/notion.yaml` by default.
Override with `--config path/to/notion.yaml`.

### Config structure

```yaml
default_project: genbooks
projects:
  genbooks:
    project_id: "..."
    database_id: "..."          # tickets database
    epics_database_id: "..."    # epics database
    prop_epic: "Related Genbook | Epics"
    prop_sprint: "Sprint"
    prop_sprint_date: "Start Date"
    epic_status_type: "select"  # or "status"
users:
  cle: "user-id-here"
  huy: "user-id-here"
```

## Commands

### Create a ticket

```bash
uv run /home/cle/.claude/skills/notion/notion_cli.py create \
  --title "Fix auth bug" \
  --description "Login fails on mobile devices" \
  --priority High \
  --assignee cle \
  --epic "Sprint Planning v2" \
  --project genbooks
```

**Options:**
- `--title` (required): Ticket title
- `--description`: Markdown description (added as page content)
- `--priority`: Low | Medium | High | Critical (default: Medium)
- `--status`: Not started | In progress | Done | Backlog
- `--assignee`: User name from config
- `--epic`: Epic name (searches epics database to link)
- `--project`: Project key from config

### Update a ticket

```bash
uv run /home/cle/.claude/skills/notion/notion_cli.py update \
  --page-id "abc123-def456" \
  --status "In progress" \
  --priority High \
  --assignee huy
```

**Options:**
- `--page-id` (required): Notion page ID to update
- `--title`: New title
- `--status`: Not started | In progress | Done | Backlog
- `--priority`: Low | Medium | High | Critical
- `--assignee`: New assignee name
- `--description`: New description (replaces existing page content)

### Search tickets

```bash
uv run /home/cle/.claude/skills/notion/notion_cli.py search \
  --assignee cle \
  --status "In progress" \
  --project genbooks
```

**Options:**
- `--assignee`: Filter by assignee name
- `--status`: Filter by status
- `--project`: Project key

**Output:** Lists tickets with ID, name, status, priority, assignee, and URL.

### List epics

```bash
uv run /home/cle/.claude/skills/notion/notion_cli.py epics \
  --status "In progress" \
  --project genbooks
```

**Options:**
- `--status`: Filter by epic status
- `--project`: Project key

### Discover users

```bash
uv run /home/cle/.claude/skills/notion/notion_cli.py users
```

Lists all workspace users (type=person) with their IDs. Shows which users are already in config.

## Output Format

All commands print human-readable output. Key IDs (page ID, ticket ID, URL) are printed on separate lines for easy parsing:

```
Created: Fix auth bug
Ticket: GB-456
ID: abc123-def456-...
URL: https://www.notion.so/...
```

## Error Handling

- Missing `NOTION_TOKEN`: exits with error message
- Unknown assignee: shows available user names from config
- API errors: prints HTTP status code and error body
- Missing config: exits with error listing checked paths
