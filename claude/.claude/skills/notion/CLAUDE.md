# Notion CLI Development Rules

## Stack

- **CLI**: typer (not argparse)
- **Models**: pydantic `BaseModel` for config and domain objects
- **Type-checking**: basedpyright — must pass clean
- **HTTP**: stdlib urllib + certifi (no httpx)
- **Single file**: everything lives in `notion_cli.py`, run via `uv run`

## Type-Checking

pyrightconfig.json suppresses only `reportExplicitAny` and `reportAny`. These are structural — every `dict[str, Any]` at the Notion API boundary cascades `Any` through `.get()` calls. This is unfixable without modeling the full Notion API response schema.

All other basedpyright strict checks are enabled. Do not add more suppressions without justification.

## Status Enum vs Free-Form String

The `Status` enum (`Not started`, `In progress`, `Done`, `Backlog`) is used only for `create` and `update` commands where we **set** a value. For `search` and `epics` commands where we **filter**, use `str | None` because Notion databases contain custom statuses (e.g. `Review`, `Staging`, `Confirmed`, `Ready for dev`) that aren't in the enum.

Same principle applies to any property that could have project-specific values.

## Multi-Project Querying

When `--project` is omitted, commands query **all** configured projects. Combined results must be re-sorted by date (`Ticket.resolve_date()`) since per-project results arrive in order but interleaving is not guaranteed.

## Typer Patterns

- `typer.Option(parser=...)` for custom type parsing (e.g. `date.fromisoformat` for `--since`). Typer does not natively support `datetime.date`.
- Shared `Annotated` type aliases (e.g. `SinceOption`) for options reused across commands.
- Module-level `_config: Config | None` and `_token: str` set in the `@app.callback()` — not a `dict[str, Any]` state bag.

## Pydantic Models

- `ConfigDict(extra="ignore")` on config models — the YAML config contains fields the CLI doesn't use.
- `Ticket.from_page()` / `Epic.from_page()` classmethods encapsulate all Notion property reading.
- `Ticket.display()` is the single source of truth for terminal output formatting. Do not inline display logic in commands.

## Notion API Boundary

- `_rich_text()` must chunk content into 2000-char segments (Notion's per-element limit).
- `_query_database()` must shallow-copy the body dict before paginating (it mutates `start_cursor`).
- `_find_epic_id()` uses a title filter, not a full table scan.
