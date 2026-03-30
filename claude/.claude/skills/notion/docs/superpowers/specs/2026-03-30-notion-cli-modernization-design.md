# Notion CLI Modernization: Typer + Pydantic + Type Safety

## Goal

Modernize `notion_cli.py` from argparse + raw dicts to typer + pydantic models, with strict type-checking via basedpyright. Fix all critical and important bugs from code review. Keep it as a single file runnable via `uv run`.

## Dependencies

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["typer", "pydantic", "pyyaml", "certifi"]
# ///
```

Typer brings `rich` and `click` transitively. Pydantic added for models. argparse removed.

## Pydantic Models

### Config Models

```python
class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    database_id: str
    epics_database_id: str = ""
    prop_epic: str = "Epic"
    epic_status_type: Literal["select", "status"] = "select"

class Config(BaseModel):
    model_config = ConfigDict(extra="ignore")

    default_project: str = ""
    projects: dict[str, ProjectConfig] = {}
    users: dict[str, str] = {}
```

Validates YAML at parse time. `extra="ignore"` lets config contain fields the CLI doesn't use (e.g. `project_id`, `tickets_data_source_id`).

### Domain Models

```python
class Ticket(BaseModel):
    ticket_id: str = ""
    name: str = ""
    status: str = ""
    priority: str = ""
    assignee: str = ""
    ah: float | None = None
    sort_date: str = ""
    created: str = ""
    edited: str = ""
    gitlab_mr: str = ""
    url: str = ""
    page_id: str = ""
    type_: str = ""

    @classmethod
    def from_page(cls, page: dict[str, Any]) -> "Ticket":
        """Extract ticket from Notion API page response using _read_* helpers."""
        ...

    def display(self, indent: str = "  ", reason: str = "") -> str:
        """Formatted terminal output. Replaces 3x copy-pasted display blocks."""
        ...

    def resolve_date(self) -> str:
        """Best date: sort_date, fallback to created."""
        ...

class Epic(BaseModel):
    name: str = ""
    status: str = ""
    phase: str = ""
    url: str = ""
    page_id: str = ""

    @classmethod
    def from_page(cls, page: dict[str, Any]) -> "Epic":
        ...

    def display(self) -> str:
        ...
```

### Enums

```python
class Priority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class Status(str, Enum):
    NOT_STARTED = "Not started"
    IN_PROGRESS = "In progress"
    DONE = "Done"
    BACKLOG = "Backlog"

class Period(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
```

## API Layer

Unchanged: urllib + certifi, raw dicts in/out. Three fixes:

1. `_request` catches `urllib.error.URLError` for network errors (not just `HTTPError`)
2. `_query_database` copies body before mutating: `payload = dict(body) if body else {}`
3. `_rich_text` splits content into 2000-char chunks per Notion's limit

Token validation moves from lazy `_headers()` check to the typer callback (runs once at startup).

## Typer CLI Structure

```python
app = typer.Typer(help="Notion ticket and epic CLI")

_state: dict[str, Any] = {}  # holds "config": Config after callback runs

@app.callback()
def main(config: Annotated[str | None, typer.Option(help="Path to notion.yaml")] = None) -> None:
    """Validate NOTION_TOKEN, load and store Config in _state."""
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("Error: NOTION_TOKEN not set", file=sys.stderr)
        raise typer.Exit(1)
    _state["config"] = load_config(config)

def get_config() -> Config:
    """Retrieve loaded config. Called by commands."""
    return _state["config"]
```

### Commands

All commands use `Annotated[..., typer.Option()]` for type-safe arguments.

- **create**: `--title` (required), `--description`, `--priority` (Priority enum), `--status` (Status enum | None), `--assignee`, `--epic`, `--project`
- **update**: `--page-id` (required), `--title`, `--status`, `--priority`, `--assignee`, `--ah`, `--description`, `--project` (NEW: was missing)
- **search**: `--assignee`, `--status`, `--query`, `--since` (validated YYYY-MM-DD), `--limit` (default 50), `--project`
- **stale**: `--assignee`, `--since` (NEW), `--limit` (NEW, default 50), `--project`
- **report**: `--period` (Period enum), `--assignee`, `--since` (NEW), `--project`
- **get-ticket**: `ticket` (positional Argument), `--project`
- **epics**: `--status`, `--project`
- **users**: no args

`--since` uses a typer callback that validates `YYYY-MM-DD` format.

`_find_epic_id` uses a Notion title filter instead of fetching all epics. The unused `status_type` parameter is removed.

## File Layout

```
 1. PEP 723 script metadata
 2. Module docstring
 3. Imports
 4. Constants (NOTION_API_URL, NOTION_VERSION, SSL_CTX, DEFAULT_CONFIG_PATHS)
 5. Enums (Priority, Status, Period)
 6. Pydantic models (Config, ProjectConfig, Ticket, Epic)
 7. Config loading (load_config -> Config, get_project_config, resolve_user_id)
 8. HTTP helpers (_headers, _request, _post, _patch, _get)
 9. Property readers (_read_title, _read_status, etc. -- called by from_page)
10. Block helpers (_rich_text, _markdown_to_blocks, _read_page_content, _replace_page_blocks)
11. Query helpers (_query_database, _build_ticket_query)
12. Date formatting (_format_dt, _format_date, _format_relative)
13. Typer app + callback
14. Commands (create, update, search, stale, epics, report, get_ticket, users)
15. if __name__ == "__main__": app()
```

## Bug Fixes Incorporated

| # | Issue | Fix Location |
|---|-------|-------------|
| 1 | `_query_database` mutates caller's body | `_query_database` copies dict |
| 2 | `_find_epic_id` full table scan | Use Notion title filter |
| 3 | 2000-char rich_text limit | `_rich_text` chunks content |
| 4 | `URLError` not caught | `_request` catches it |
| 5 | Token validated lazily | Typer callback validates at startup |
| 6 | `update` missing `--project` | Added to command |
| 7 | Display logic 3x copy-paste | `Ticket.display()` method |
| 8 | `--since` not validated | Typer callback validates YYYY-MM-DD |
| 9 | `stale` unbounded fetch | Added `--since` and `--limit` |
| 10 | `report` unbounded fetch | Added `--since` |

## What's NOT Changing

- HTTP layer (urllib + certifi, no httpx)
- Output format (human-readable text, no --json)
- Config file format (same YAML structure, pydantic just validates it)
- Invocation (`uv run notion_cli.py <command>`)
- Single file architecture

## Type Checking

Target: basedpyright passes clean. Key considerations:
- All function signatures fully typed
- `dict[str, Any]` at the Notion API boundary only (raw responses)
- Typed models everywhere else
- Enums for constrained string choices
- `Annotated` types for typer parameters
