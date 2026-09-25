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

Reads from the skill-local `notion.yaml` by default, then `./config/notion.yaml` if the skill-local file is absent.
Override with `--config path/to/notion.yaml`.

### Config structure

```yaml
default_project: genbooks
default_creator_alias: cle
projects:
  genbooks:
    project_id: "..."
    database_id: "..."          # tickets database
    tickets_data_source_id: "..." # tickets data source for page creation
    sprints_data_source_id: "..." # sprints database/data source
    epics_database_id: "..."    # epics database
    prop_epic: "Related Genbook | Epics"
    prop_epic_id: "..."         # required for data-source-backed create payloads
    prop_sprint: "Sprint"       # ticket relation property
    prop_sprint_id: "..."       # required for data-source-backed create payloads
    prop_sprint_date: "Start Date" # sprint start-date property
    prop_title_id: "..."        # required for data-source-backed create payloads
    prop_assignee_id: "..."     # required for data-source-backed create payloads
    prop_priority_id: "..."     # required for data-source-backed create payloads
    prop_status_id: "..."       # required for data-source-backed create payloads
    ticket_status_type: status  # or "select"
    status_name_overrides: {}   # CLI status -> project-specific Notion option
    epic_status_type: "select"  # or "status"
users:
  cle: "user-id-here"
  huy: "user-id-here"
```

## Commands

### Project routing

- Use `--project data-platform` for Data Platform work, including every Entity Registry ticket.
- Use an epic from `Data Platform | Epics` whose `Service` is `Entity Registry` for Entity Registry tickets.
- Continue using `--project genbook-global` for Genbook Global tickets.
- Always pass `--project` explicitly when creating a ticket so topic-based routing is unambiguous.

### Create a ticket

**Required ticket defaults:**

- Always assign the ticket to the creator. The CLI uses `default_creator_alias` from config when `--assignee` is omitted; pass an explicit `--assignee` when the creator differs.
- Always set the ticket's `Sprint` relation to the current active sprint for the selected project. The CLI resolves it from the project's configured sprint source using today's local date and `prop_sprint_date`.
- Always set the ticket's Epic relation by passing `--epic` with an existing epic name for the selected project.
- For data-source-backed projects, configure all `prop_*_id` values used by create payloads.
- If the creator, current active sprint, configured epic source, named epic, or required create property IDs cannot be resolved, stop and report the missing mapping/source instead of creating an incomplete ticket.

```bash
uv run /home/cle/.claude/skills/notion/notion_cli.py create \
  --title "Add Entity Registry health check" \
  --description "Expose and verify the registry health endpoint" \
  --priority High \
  --assignee cle \
  --epic "Build Entity Registry" \
  --project data-platform
```

**Options:**
- `--title` (required): Ticket title
- `--description`: Ticket description (added as page content)
- `--priority`: Low | Medium | High | Critical (default: Medium)
- `--status`: Not started | In progress | Done | Backlog | Closed
- `--assignee`: User name from config. Optional only when `default_creator_alias` is configured; use the creator alias.
- `--epic` (required): Existing epic name for the selected project. The CLI fails before ticket creation if it is omitted, the project has no epic database, or the name cannot be found.
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
  --page-id "GB-319" \
  --status "In progress" \
  --priority High \
  --assignee huy \
  --epic "Sprint Planning v2" \
  --project genbooks
```

**Options:**
- `--page-id` (required): Ticket ID (e.g. `GB-319`) or Notion page UUID to update
- `--title`: New title
- `--status`: Not started | In progress | Done | Backlog | Closed
- `--priority`: Low | Medium | High | Critical
- `--ah`: Actual working hours (number)
- `--assignee`: New assignee name
- `--epic`: Existing epic name to link. Uses the selected project's configured epic database and relation property.
- `--description`: New description (replaces existing page content)
- `--project`: Project key from config

### Bulk update many tickets

```bash
uv run /home/cle/.claude/skills/notion/notion_cli.py bulk SN-199 SN-200 SN-201 \
  --priority High \
  --status "In progress" \
  --project data-platform
```

**Arguments:**
- `tickets` (required, one or more): Ticket IDs or page UUIDs

**Options:** same fields as `update` (`--title`, `--status`, `--priority`, `--assignee`, `--epic`, `--ah`, `--project`). At least one field is required. `--description` is not supported in bulk.

**Output:** One `OK`/`FAIL` line per ticket, then a summary. Exits non-zero if any ticket failed. Unresolvable tickets are reported as `FAIL …: not found` and skipped.

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
- `--json`: Print a machine-readable JSON array instead of the human table

All filters combine with AND logic.

**Output:** Lists tickets sorted by Sort Date (newest first) with ID, name, status, priority, assignee, AH, MR (if present), dates (Sort/Created/Updated with relative times), and URL. With `--json`, prints a JSON array of flat objects (`id`, `name`, `status`, `priority`, `assignee`, `ah`, `due_date`, `sort_date`, `created`, `edited`, `gitlab_mr`, `url`, `page_id`, `type`).

### Get ticket details

```bash
uv run /home/cle/.claude/skills/notion/notion_cli.py get-ticket GB-319
uv run /home/cle/.claude/skills/notion/notion_cli.py get-ticket 3db52639-55bd-4228-90f7-298586ddaa98
```

Accepts either a human-readable ticket ID (e.g. `GB-319`) or a Notion page UUID. Shows full ticket detail, the page UUID on an `ID:` line, and the complete description.

**Options:**
- `ticket` (required, positional): Ticket ID or page UUID
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
- `--since`: Filter by Due Date >= YYYY-MM-DD
- `--project`: Project key

**Output:** Table showing ticket count, total AH, and average AH per Due Date period, sorted newest first, with a summary line.

### AH week reconciliation

```bash
uv run /home/cle/.claude/skills/notion/notion_cli.py ah-week                 # pull
uv run /home/cle/.claude/skills/notion/notion_cli.py ah-week --diff          # show edits vs baseline
uv run /home/cle/.claude/skills/notion/notion_cli.py ah-week --report        # AH totals from CSV
uv run /home/cle/.claude/skills/notion/notion_cli.py ah-week --apply         # push to Notion
```

Weekly ticket/AH reconciliation through a local CSV. The default (no flags) pulls the current Mon–Sun week's tickets for `default_creator_alias` (or `--assignee`) across all configured projects, filters by Sort Date client-side, and writes `ah-week-<year>-W<week>.csv` (override with `--out`) with columns `id,name,status,priority,ah,mr,sort_date,notion_url`, plus a hidden `<csv>.baseline` snapshot.

**MR column**: when `GITLAB_TOKEN` is set, scans every repo listed in `/home/cle/.claude/skills/gitlab/repos.yaml` (all MR states, ticket ids matched in MR titles; merged > opened, most recent wins). Falls back to the Notion Gitlab MR property; prints a warning when scanning is skipped.

**Workflow**: pull → edit the CSV (status, priority, ah, mr) → `--diff` to review → `--apply` to push. `--apply` pushes only Notion-updatable changed fields (status, priority, ah) with the correct project per ticket; changed `mr` values are listed as local-only (the Notion API has no MR update from this CLI). On full success the baseline is refreshed; on any FAIL the baseline is left untouched and the exit code is non-zero. Re-pulling keeps user-edited cells and only refreshes unedited fields.

**Options:**
- `--diff`: compare the CSV against its `.baseline` on status/priority/ah/mr; reports added/removed rows
- `--report`: total AH, avg per day (7-day and 5-day), per-project and per-status totals, per-ticket table
- `--apply`: push the diff to Notion, then refresh the baseline
- `--out`: CSV path (default: `ah-week-<ISO year>-W<ISO week>.csv` in the cwd)
- `--assignee`: assignee name (default: `default_creator_alias`)
- `--since` / `--until`: override the week window with explicit YYYY-MM-DD dates

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

- The integration cannot delete or archive pages (`delete_content` / `archive_content` not granted) — close tickets by setting Status to `Closed` instead; hard deletion must be done in the Notion UI
- Missing `NOTION_TOKEN`: exits with error message
- Unknown assignee: shows available user names from config
- Missing or unknown epic on create: exits before creating a ticket
- API errors: prints HTTP status code and error body
- Missing config: exits with error listing checked paths
