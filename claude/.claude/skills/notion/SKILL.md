---
name: notion
description: >
  Manage Notion tickets and epics via CLI. Use this skill whenever you need to create tickets,
  search tasks, update ticket status/priority/assignee, list epics, or discover workspace users.
  Even if the user doesn't mention "notion" by name — if they want to track work, manage tasks,
  check sprint status, or update ticket progress, use this skill.
---

# Notion CLI

Standalone Python CLI for Notion ticket/epic operations. Runs via `uv` with inline script dependencies (typer, pydantic, pyyaml, certifi).

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
- `--description`: Ticket description (added as page content)
- `--priority`: Low | Medium | High | Critical (default: Medium)
- `--status`: Not started | In progress | Done | Backlog
- `--assignee`: User name from config
- `--epic`: Epic name (searches epics database to link)
- `--project`: Project key from config

**Description convention:** When creating tickets, format the `--description` with this structure:

```
## Context
Why this ticket exists — the problem, trigger, or motivation.

## What
What needs to be done — specific changes, scope.

## Acceptance Criteria
- [ ] Concrete conditions that define "done"
```

Omit sections that don't apply (e.g., a simple bug fix might skip Acceptance Criteria).

### Update a ticket

```bash
uv run /home/cle/.claude/skills/notion/notion_cli.py update \
  --page-id "abc123-def456" \
  --status "In progress" \
  --priority High \
  --assignee huy \
  --project genbooks
```

**Options:**
- `--page-id` (required): Notion page ID to update
- `--title`: New title
- `--status`: Not started | In progress | Done | Backlog
- `--priority`: Low | Medium | High | Critical
- `--ah`: Actual working hours (number)
- `--assignee`: New assignee name
- `--description`: New description (replaces existing page content)
- `--project`: Project key from config

### Search tickets

```bash
uv run /home/cle/.claude/skills/notion/notion_cli.py search \
  --assignee cle \
  --status "In progress" \
  --query "auth" \
  --since 2026-03-01 \
  --limit 20 \
  --project genbooks
```

**Options:**
- `--assignee`: Filter by assignee name
- `--status`: Filter by status
- `--query`: Search by title (case-insensitive substring)
- `--since`: Filter by Sort Date >= YYYY-MM-DD
- `--limit`: Max results to display (default: 50, 0 for all)
- `--project`: Project key

All filters combine with AND logic.

**Output:** Lists tickets sorted by Sort Date (newest first) with ID, name, status, priority, assignee, AH, MR (if present), dates (Sort/Created/Updated with relative times), and URL.

### Get ticket details

```bash
uv run /home/cle/.claude/skills/notion/notion_cli.py get-ticket GB-319
uv run /home/cle/.claude/skills/notion/notion_cli.py get-ticket 3db52639-55bd-4228-90f7-298586ddaa98
```

Accepts either a human-readable ticket ID (e.g. `GB-319`) or a Notion page ID. Shows full ticket detail including the complete description.

**Options:**
- `ticket` (required, positional): Ticket ID or page ID
- `--project`: Project key

### List stale tickets

```bash
uv run /home/cle/.claude/skills/notion/notion_cli.py stale \
  --assignee cle \
  --since 2026-03-01 \
  --limit 20 \
  --project genbooks
```

**Options:**
- `--assignee`: Filter by assignee name
- `--since`: Filter by Sort Date >= YYYY-MM-DD
- `--limit`: Max results to display (default: 50, 0 for all)
- `--project`: Project key

**Output:** Lists tickets that have empty status or no AH logged, with a reason tag (e.g. `[no status, no AH]`).

### AH report

```bash
uv run /home/cle/.claude/skills/notion/notion_cli.py report \
  --period weekly \
  --assignee cle \
  --since 2026-03-01 \
  --project genbooks
```

**Options:**
- `--period`: `weekly` (default) or `monthly`
- `--assignee`: Filter by assignee name
- `--since`: Filter by Sort Date >= YYYY-MM-DD
- `--project`: Project key

**Output:** Table showing ticket count, total AH, and average AH per period, sorted newest first, with a summary line.

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
