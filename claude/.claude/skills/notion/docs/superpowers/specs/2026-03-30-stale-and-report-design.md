# Notion CLI: Stale Tickets & AH Report

## Goal

Add two new subcommands to `notion_cli.py` that answer:
1. Which tickets are stale (no AH logged, or status unset)?
2. How many AH are logged per week/month, and what's the distribution?

## New Subcommands

### `stale`

```
notion_cli.py stale [--assignee NAME] [--project PROJECT]
```

Fetches all tickets, filters client-side for:
- **Status is empty string** (truly unset, not "Backlog" or "Not started")
- **AH is null**

A ticket matching either condition is stale. Results sorted by Sort Date descending (fallback to Created time).

Output uses the same 4-line format as `search`, with a stale reason tag on the title line:

```
Found 5 stale ticket(s):

  [GB-1492] Fix s3_to_gdrive S3 path resolution  [no status, no AH]
    Status:  | Priority: Medium | Assignee: cle | AH: -
    Sort: 2026-03-27 | Created: 2026-03-27 10:33 (2d ago) | Updated: 2026-03-27 10:33 (2d ago)
    URL: https://...
```

Tag values: `[no status]`, `[no AH]`, or `[no status, no AH]`.

### `report`

```
notion_cli.py report [--period weekly|monthly] [--assignee NAME] [--project PROJECT]
```

Defaults: `--period weekly`, no assignee filter.

Fetches all tickets, filters to those with AH > 0. Groups by date period using Sort Date (fallback to Created time). Skips tickets where both dates are empty/epoch.

- Weekly grouping: ISO week format `2026-W13`
- Monthly grouping: `2026-03`

Output:

```
AH Report (weekly) — genbooks

Period      Tickets  Total AH  Avg AH
2026-W13    8        24        3.0
2026-W12    12       36        3.0
2026-W11    5        18        3.6

Summary: 25 tickets, 78 AH total, 3.1 avg
```

Periods sorted newest first. Avg AH rounded to 1 decimal.

## Shared Infrastructure

### `_read_ticket(page) -> dict`

Extracts common fields from a Notion page into a flat dict:

```python
{
    "ticket_id": "GB-123",
    "name": "Fix auth bug",
    "status": "Done",
    "priority": "High",
    "assignee": "cle",
    "ah": 4,
    "sort_date": "2026-03-28T00:00:00.000+00:00",
    "created": "2026-03-28T01:54:00.000Z",
    "edited": "2026-03-28T02:09:00.000Z",
    "url": "https://...",
    "page_id": "abc-123",
}
```

### `_build_ticket_query(config, args) -> dict`

Builds the Notion database query body with:
- Optional assignee filter (from `args.assignee`)
- Default sort: Sort Date descending
- Page size: 100

### Refactor `cmd_search`

Update to use `_read_ticket` and `_build_ticket_query` to reduce duplication.

## CLI Registration

Add `stale` and `report` to the argparse subparsers:

- `stale`: `--assignee`, `--project`
- `report`: `--period` (choices: `weekly`, `monthly`, default: `weekly`), `--assignee`, `--project`

## SKILL.md Updates

Add documentation for both new commands with usage examples.

## Scope

- No new dependencies (stdlib `datetime` already imported)
- No config changes
- No changes to `create`, `update`, `epics`, or `users` commands
- Client-side filtering and aggregation (data volumes are hundreds, not thousands)
