#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["typer", "pydantic", "pyyaml", "certifi"]
# ///
"""Notion CLI for ticket and epic management.

Standalone CLI that wraps the Notion API for creating, updating,
and searching tickets and epics. Uses typer for CLI, pydantic for
models, and stdlib urllib for HTTP.

Environment:
    NOTION_TOKEN: Required. Notion integration token.

Config:
    Reads from ./config/notion.yaml or ~/Source/claude-boy/config/notion.yaml.
    Override with --config flag.
"""

from __future__ import annotations

import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal

import certifi
import typer
import yaml
from pydantic import BaseModel, ConfigDict

# =============================================================================
# Constants
# =============================================================================

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
SSL_CTX = ssl.create_default_context(cafile=certifi.where())

DEFAULT_CONFIG_PATHS = [
    Path(__file__).resolve().parent / "config" / "notion.yaml",
    Path("./config/notion.yaml"),
    Path.home() / "Source" / "claude-boy" / "config" / "notion.yaml",
]


# =============================================================================
# Enums
# =============================================================================


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


# =============================================================================
# Pydantic Models
# =============================================================================


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")  # pyright: ignore[reportUnannotatedClassAttribute]

    database_id: str
    epics_database_id: str = ""
    prop_epic: str = "Epic"
    epic_status_type: Literal["select", "status"] = "select"
    date_property: str = "Sort Date"
    date_property_type: str = "formula"


class Config(BaseModel):
    model_config = ConfigDict(extra="ignore")  # pyright: ignore[reportUnannotatedClassAttribute]

    default_project: str = ""
    projects: dict[str, ProjectConfig] = {}
    users: dict[str, str] = {}


_EPOCH_PREFIX = "1970-01-01"


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
    def from_page(cls, page: dict[str, Any]) -> Ticket:
        """Extract ticket from Notion API page response using _read_* helpers."""
        props = page.get("properties", {})
        return cls(
            ticket_id=_read_unique_id(props),
            name=_read_title(props),
            status=_read_status(props),
            priority=_read_select(props, "Priority"),
            assignee=_read_people(props),
            ah=_read_number(props, "AH"),
            sort_date=_read_formula_date(props, "Sort Date"),
            created=_read_timestamp(props, "Created time"),
            edited=_read_timestamp(props, "Last edited time"),
            gitlab_mr=_read_url(props, "Gitlab MR"),
            url=page.get("url", ""),
            page_id=page.get("id", ""),
            type_=_read_select(props, "Type"),
        )

    def display(self, indent: str = "  ", reason: str = "", show_type: bool = False) -> str:
        """Formatted terminal output."""
        ah_str = str(self.ah) if self.ah is not None else "-"
        label = f"[{self.ticket_id}]" if self.ticket_id else f"[{self.page_id[:8]}]"
        type_part = f" [{self.type_}]" if show_type and self.type_ else ""
        reason_part = f"  [{reason}]" if reason else ""
        lines = [
            f"{indent}{label}{type_part} {self.name}{reason_part}",
            f"{indent}  Status: {self.status} | Priority: {self.priority} | Assignee: {self.assignee} | AH: {ah_str}",
            f"{indent}  Sort: {_format_date(self.sort_date)} | Created: {_format_dt(self.created)} ({_format_relative(self.created)}) | Updated: {_format_dt(self.edited)} ({_format_relative(self.edited)})",
        ]
        if self.gitlab_mr:
            lines.append(f"{indent}  MR: {self.gitlab_mr}")
        lines.append(f"{indent}  URL: {self.url}")
        return "\n".join(lines)

    def resolve_date(self) -> str:
        """Best date: sort_date, fallback to created."""
        sd = self.sort_date
        if sd and not sd.startswith(_EPOCH_PREFIX):
            return sd
        ct = self.created
        if ct and not ct.startswith(_EPOCH_PREFIX):
            return ct
        return ""


class Epic(BaseModel):
    name: str = ""
    status: str = ""
    phase: str = ""
    url: str = ""
    page_id: str = ""

    @classmethod
    def from_page(cls, page: dict[str, Any]) -> Epic:
        """Extract epic from Notion API page response."""
        props = page.get("properties", {})
        return cls(
            name=_read_title(props, "Epic") or _read_title(props, "Name"),
            status=_read_status(props),
            phase=_read_select(props, "Phase"),
            url=page.get("url", ""),
            page_id=page.get("id", ""),
        )

    def display(self) -> str:
        """Formatted terminal output for an epic."""
        lines = [
            f"  {self.name}",
            f"    Status: {self.status} | Phase: {self.phase}",
            f"    ID: {self.page_id}",
            f"    URL: {self.url}",
        ]
        return "\n".join(lines)


# =============================================================================
# Config loading
# =============================================================================


def load_config(config_path: str | None = None) -> Config:
    """Load config from YAML file."""
    if config_path:
        p = Path(config_path)
        if not p.exists():
            print(f"Error: config not found at {p}", file=sys.stderr)
            sys.exit(1)
        with open(p) as f:
            raw = dict(yaml.safe_load(f) or {})
            return Config.model_validate(raw)

    for p in DEFAULT_CONFIG_PATHS:
        if p.exists():
            with open(p) as f:
                default_raw = dict(yaml.safe_load(f) or {})
                return Config.model_validate(default_raw)

    return Config()


def get_project_config(config: Config, project: str | None = None) -> ProjectConfig:
    """Get project-specific config."""
    key = project or config.default_project
    if key not in config.projects:
        available = ", ".join(config.projects.keys())
        print(f"Error: unknown project '{key}'. Available: {available}", file=sys.stderr)
        sys.exit(1)
    return config.projects[key]


def resolve_user_id(config: Config, name: str) -> str | None:
    """Look up user ID by name (case-insensitive)."""
    return config.users.get(name.lower())


# =============================================================================
# HTTP helpers
# =============================================================================


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _request(method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Make a Notion API request."""
    url = f"{NOTION_API_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=_headers(), method=method)

    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"API Error ({e.code}): {error_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network Error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def _post(path: str, body: dict[str, Any]) -> dict[str, Any]:
    return _request("POST", path, body)


def _patch(path: str, body: dict[str, Any]) -> dict[str, Any]:
    return _request("PATCH", path, body)


def _get(path: str) -> dict[str, Any]:
    return _request("GET", path)


# =============================================================================
# Property readers
# =============================================================================


def _read_title(props: dict[str, Any], key: str = "Name") -> str:
    """Extract plain text from a title property."""
    title = props.get(key, {}).get("title", [])
    return title[0]["plain_text"] if title else ""


def _read_status(props: dict[str, Any]) -> str:
    """Read status from either status or select type."""
    raw = props.get("Status", {})
    prop_type = raw.get("type", "")
    val = raw.get(prop_type, {})
    return val.get("name", "") if val else ""


def _read_select(props: dict[str, Any], key: str) -> str:
    sel = props.get(key, {}).get("select", {})
    return sel.get("name", "") if sel else ""


def _read_people(props: dict[str, Any], key: str = "Assignee") -> str:
    people = props.get(key, {}).get("people", [])
    return people[0].get("name", "") if people else ""


def _read_unique_id(props: dict[str, Any]) -> str:
    """Extract human-readable ticket ID (e.g. 'GB-123')."""
    for raw_prop in props.values():
        prop: dict[str, Any] = raw_prop if isinstance(raw_prop, dict) else {}  # pyright: ignore[reportUnknownVariableType]
        if prop.get("type") == "unique_id":
            uid: dict[str, Any] = prop.get("unique_id") or {}
            prefix = str(uid.get("prefix", ""))
            number_val = uid.get("number")
            if prefix and number_val is not None:
                return f"{prefix}-{number_val}"
    return ""


def _read_url(props: dict[str, Any], key: str) -> str:
    return props.get(key, {}).get("url", "") or ""


def _read_number(props: dict[str, Any], key: str) -> float | None:
    val = props.get(key, {}).get("number")
    if val is None:
        return None
    return float(val)


def _read_timestamp(props: dict[str, Any], key: str) -> str:
    """Read created_time or last_edited_time property."""
    raw = props.get(key, {})
    prop_type = raw.get("type", "")
    return raw.get(prop_type, "") or ""


def _read_formula_date(props: dict[str, Any], key: str) -> str:
    """Read a formula property that returns a date."""
    raw = props.get(key, {}).get("formula", {})
    if raw.get("type") == "date" and raw.get("date"):
        return raw["date"].get("start", "") or ""
    return ""


# =============================================================================
# Block helpers
# =============================================================================


def _rich_text(content: str) -> list[dict[str, Any]]:
    """Build rich_text array, splitting into 2000-char chunks per Notion limit."""
    if not content:
        return [{"type": "text", "text": {"content": ""}}]
    chunks: list[dict[str, Any]] = []
    for i in range(0, len(content), 2000):
        chunks.append({"type": "text", "text": {"content": content[i : i + 2000]}})
    return chunks


def _markdown_to_blocks(text: str) -> list[dict[str, Any]]:
    """Convert markdown text to Notion blocks.

    Supports headings (h1-h3), to-do items, bulleted lists, and paragraphs.
    Consecutive plain-text lines are joined into a single paragraph block.
    """
    if not text:
        return []

    blocks: list[dict[str, Any]] = []
    paragraph_lines: list[str] = []

    def _flush_paragraph() -> None:
        if paragraph_lines:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": _rich_text("\n".join(paragraph_lines))},
            })
            paragraph_lines.clear()

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            _flush_paragraph()
            continue

        # Headings
        heading_match = re.match(r"^(#{1,3})\s+(.*)", stripped)
        if heading_match:
            _flush_paragraph()
            level = len(heading_match.group(1))
            heading_type = f"heading_{level}"
            blocks.append({
                "object": "block",
                "type": heading_type,
                heading_type: {"rich_text": _rich_text(heading_match.group(2).strip())},
            })
            continue

        # To-do items (checked)
        todo_checked = re.match(r"^- \[x\]\s+(.*)", stripped, re.IGNORECASE)
        if todo_checked:
            _flush_paragraph()
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {"rich_text": _rich_text(todo_checked.group(1).strip()), "checked": True},
            })
            continue

        # To-do items (unchecked)
        todo_unchecked = re.match(r"^- \[ \]\s+(.*)", stripped)
        if todo_unchecked:
            _flush_paragraph()
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {"rich_text": _rich_text(todo_unchecked.group(1).strip()), "checked": False},
            })
            continue

        # Bulleted list items
        bullet_match = re.match(r"^- (.*)", stripped)
        if bullet_match:
            _flush_paragraph()
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": _rich_text(bullet_match.group(1).strip())},
            })
            continue

        # Plain text — accumulate for paragraph grouping
        paragraph_lines.append(stripped)

    _flush_paragraph()
    return blocks


def _read_page_content(page_id: str) -> str:
    """Read all text content from a page's children blocks."""
    parts: list[str] = []
    url = f"/blocks/{page_id}/children"
    while True:
        resp = _get(url)
        for block in resp.get("results", []):
            btype = block.get("type", "")
            texts = block.get(btype, {}).get("rich_text", [])
            text = "".join(t.get("plain_text", "") for t in texts)
            if text:
                parts.append(text)
        if not resp.get("has_more"):
            break
        url = f"/blocks/{page_id}/children?start_cursor={resp['next_cursor']}"
    return "\n\n".join(parts)


def _replace_page_blocks(page_id: str, new_blocks: list[dict[str, Any]]) -> None:
    """Replace all blocks in a page."""
    # Collect all block IDs first to avoid cursor invalidation during deletion
    block_ids: list[str] = []
    url = f"/blocks/{page_id}/children"
    while True:
        existing = _get(url)
        for block in existing.get("results", []):
            block_ids.append(block["id"])
        if not existing.get("has_more"):
            break
        url = f"/blocks/{page_id}/children?start_cursor={existing['next_cursor']}"

    for bid in block_ids:
        _ = _request("DELETE", f"/blocks/{bid}")

    # Append new blocks in batches of 100
    if new_blocks:
        for i in range(0, len(new_blocks), 100):
            batch = new_blocks[i : i + 100]
            _ = _patch(f"/blocks/{page_id}/children", {"children": batch})


# =============================================================================
# Query helpers
# =============================================================================


def _query_database(database_id: str, body: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Query a Notion database, handling pagination."""
    payload = dict(body) if body else {}
    all_results: list[dict[str, Any]] = []
    has_more = True
    while has_more:
        resp = _post(f"/databases/{database_id}/query", payload)
        all_results.extend(resp.get("results", []))
        has_more = resp.get("has_more", False)
        next_cursor = resp.get("next_cursor")
        if has_more and next_cursor:
            payload["start_cursor"] = next_cursor
        else:
            has_more = False
    return all_results


def _build_filter_body(
    config: Config,
    assignee: str | None = None,
    status: str | None = None,
    query: str | None = None,
    since: date | None = None,
    proj: ProjectConfig | None = None,
) -> dict[str, Any]:
    """Build filter and sort body for ticket queries.

    Uses project-level ``date_property`` (default: ``Sort Date``) for
    ``--since`` filtering and sort ordering.  The property type defaults to
    ``formula`` but can be overridden per project via ``date_property_type``
    (e.g. ``created_time``).
    """
    date_prop = proj.date_property if proj else "Sort Date"
    date_type = proj.date_property_type if proj else "formula"

    filters: list[dict[str, Any]] = []
    if assignee:
        user_id = resolve_user_id(config, assignee)
        if not user_id:
            available = ", ".join(sorted(config.users.keys()))
            print(f"Error: unknown assignee '{assignee}'. Available: {available}", file=sys.stderr)
            sys.exit(1)
        filters.append({"property": "Assignee", "people": {"contains": user_id}})
    if status:
        filters.append({"property": "Status", "status": {"equals": status}})
    if query:
        filters.append({"property": "Name", "title": {"contains": query}})
    if since:
        since_str = since.isoformat()
        if date_type == "formula":
            filters.append({"property": date_prop, "formula": {"date": {"on_or_after": since_str}}})
        elif date_type == "created_time":
            filters.append({"timestamp": "created_time", "created_time": {"on_or_after": since_str}})
        elif date_type == "last_edited_time":
            filters.append({"timestamp": "last_edited_time", "last_edited_time": {"on_or_after": since_str}})
        else:
            filters.append({"property": date_prop, "date": {"on_or_after": since_str}})

    body: dict[str, Any] = {"page_size": 100}
    if date_type in ("created_time", "last_edited_time"):
        body["sorts"] = [{"timestamp": date_type, "direction": "descending"}]
    else:
        body["sorts"] = [{"property": date_prop, "direction": "descending"}]

    if len(filters) == 1:
        body["filter"] = filters[0]
    elif len(filters) > 1:
        body["filter"] = {"and": filters}

    return body


def _build_ticket_queries(
    config: Config,
    project: str | None = None,
    assignee: str | None = None,
    status: str | None = None,
    query: str | None = None,
    since: date | None = None,
) -> list[tuple[str, str, dict[str, Any]]]:
    """Build ticket queries across projects.

    When --project is specified, queries that project only.
    When omitted, queries ALL configured projects.

    Returns list of (project_name, database_id, query_body).
    """
    if project:
        proj = get_project_config(config, project)
        body = _build_filter_body(config, assignee=assignee, status=status, query=query, since=since, proj=proj)
        return [(project, proj.database_id, body)]

    result: list[tuple[str, str, dict[str, Any]]] = []
    for name, proj in config.projects.items():
        body = _build_filter_body(config, assignee=assignee, status=status, query=query, since=since, proj=proj)
        result.append((name, proj.database_id, body))
    return result


# =============================================================================
# Date formatting
# =============================================================================


def _format_dt(iso_str: str) -> str:
    """Format ISO timestamp as 'YYYY-MM-DD HH:MM'. Returns '-' for empty/epoch."""
    if not iso_str or iso_str.startswith(_EPOCH_PREFIX):
        return "-"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return iso_str[:16]


def _format_date(iso_str: str) -> str:
    """Format ISO timestamp as 'YYYY-MM-DD'. Returns '-' for empty/epoch."""
    if not iso_str or iso_str.startswith(_EPOCH_PREFIX):
        return "-"
    return iso_str[:10]


def _format_relative(iso_str: str) -> str:
    """Format ISO timestamp as relative time (e.g. '2h ago'). Returns '-' for empty/epoch."""
    if not iso_str or iso_str.startswith(_EPOCH_PREFIX):
        return "-"
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        secs = int(delta.total_seconds())
        if secs < 0:
            return "just now"
        if secs < 60:
            return f"{secs}s ago"
        mins = secs // 60
        if mins < 60:
            return f"{mins}m ago"
        hours = mins // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        if days < 30:
            return f"{days}d ago"
        months = days // 30
        if months < 12:
            return f"{months}mo ago"
        years = days // 365
        return f"{years}y ago"
    except ValueError:
        return "-"


# =============================================================================
# Typer app + callback
# =============================================================================

app = typer.Typer(help="Notion ticket and epic CLI")

_config: Config | None = None
_token: str = ""


def _parse_since(value: str | None) -> date | None:
    """Typer callback: parse YYYY-MM-DD string into a date object."""
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise typer.BadParameter(f"Invalid date '{value}'. Expected YYYY-MM-DD.")


SinceOption = Annotated[date | None, typer.Option(help="Filter by Sort Date >= YYYY-MM-DD", parser=_parse_since)]


@app.callback()
def callback(
    config: Annotated[str | None, typer.Option(help="Path to notion.yaml")] = None,
) -> None:
    """Validate NOTION_TOKEN, load and store Config."""
    global _config, _token
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("Error: NOTION_TOKEN environment variable not set", file=sys.stderr)
        raise typer.Exit(1)
    _token = token
    _config = load_config(config)


def get_config() -> Config:
    """Retrieve loaded config. Called by commands."""
    if _config is None:
        print("Error: config not loaded", file=sys.stderr)
        raise typer.Exit(1)
    return _config


# =============================================================================
# Commands
# =============================================================================


@app.command()
def create(
    title: Annotated[str, typer.Option(help="Ticket title")],
    description: Annotated[str, typer.Option(help="Ticket description (markdown)")] = "",
    priority: Annotated[Priority, typer.Option(help="Ticket priority")] = Priority.MEDIUM,
    status: Annotated[Status | None, typer.Option(help="Ticket status")] = None,
    assignee: Annotated[str | None, typer.Option(help="Assignee name (from config users)")] = None,
    epic: Annotated[str | None, typer.Option(help="Epic name to link")] = None,
    project: Annotated[str | None, typer.Option(help="Project key")] = None,
) -> None:
    """Create a ticket."""
    config = get_config()
    proj = get_project_config(config, project)
    database_id = proj.database_id

    properties: dict[str, Any] = {
        "Name": {"title": [{"text": {"content": title}}]},
    }

    properties["Priority"] = {"select": {"name": priority.value}}

    if status is not None:
        properties["Status"] = {"status": {"name": status.value}}

    if assignee:
        user_id = resolve_user_id(config, assignee)
        if not user_id:
            available = ", ".join(sorted(config.users.keys()))
            print(f"Error: unknown assignee '{assignee}'. Available: {available}", file=sys.stderr)
            raise typer.Exit(1)
        properties["Assignee"] = {"people": [{"id": user_id}]}

    if epic:
        epics_db = proj.epics_database_id
        if epics_db:
            epic_id = _find_epic_id(epics_db, epic)
            if epic_id:
                properties[proj.prop_epic] = {"relation": [{"id": epic_id}]}
            else:
                print(f"Warning: epic '{epic}' not found, skipping epic link", file=sys.stderr)

    children = _markdown_to_blocks(description) if description else []

    payload: dict[str, Any] = {
        "parent": {"database_id": database_id},
        "properties": properties,
    }
    if children:
        payload["children"] = children

    page = _post("/pages", payload)

    page_id = page.get("id", "")
    url = page.get("url", "")
    props = page.get("properties", {})
    ticket_id = _read_unique_id(props)

    print(f"Created: {title}")
    if ticket_id:
        print(f"Ticket: {ticket_id}")
    print(f"ID: {page_id}")
    print(f"URL: {url}")


def _find_epic_id(epics_db: str, epic_name: str) -> str | None:
    """Search epics database for an epic by name using a title filter."""
    body: dict[str, Any] = {
        "filter": {
            "or": [
                {"property": "Epic", "title": {"equals": epic_name}},
                {"property": "Name", "title": {"equals": epic_name}},
            ]
        }
    }
    results = _query_database(epics_db, body)
    for page in results:
        props = page.get("properties", {})
        name = _read_title(props, "Epic") or _read_title(props, "Name")
        if name.lower() == epic_name.lower():
            return page["id"]
    return None


@app.command()
def update(
    page_id: Annotated[str, typer.Option(help="Notion page ID")],
    title: Annotated[str | None, typer.Option(help="New title")] = None,
    status: Annotated[Status | None, typer.Option(help="New status")] = None,
    priority: Annotated[Priority | None, typer.Option(help="New priority")] = None,
    assignee: Annotated[str | None, typer.Option(help="New assignee name")] = None,
    ah: Annotated[float | None, typer.Option(help="Actual working hours")] = None,
    description: Annotated[str | None, typer.Option(help="New description (replaces existing)")] = None,
    project: Annotated[str | None, typer.Option(help="Project key")] = None,
) -> None:
    """Update a ticket."""
    # project is accepted for consistency but not used for update (page_id is enough)
    _ = project
    config = get_config()
    properties: dict[str, Any] = {}

    if title:
        properties["Name"] = {"title": [{"text": {"content": title}}]}
    if status is not None:
        properties["Status"] = {"status": {"name": status.value}}
    if priority is not None:
        properties["Priority"] = {"select": {"name": priority.value}}
    if ah is not None:
        properties["AH"] = {"number": ah}
    if assignee:
        user_id = resolve_user_id(config, assignee)
        if not user_id:
            available = ", ".join(sorted(config.users.keys()))
            print(f"Error: unknown assignee '{assignee}'. Available: {available}", file=sys.stderr)
            raise typer.Exit(1)
        properties["Assignee"] = {"people": [{"id": user_id}]}

    if not properties and not description:
        print("Error: nothing to update. Provide at least one field.", file=sys.stderr)
        raise typer.Exit(1)

    if properties:
        page = _patch(f"/pages/{page_id}", {"properties": properties})
    else:
        page = _get(f"/pages/{page_id}")

    if description:
        _replace_page_blocks(page_id, _markdown_to_blocks(description))

    url = page.get("url", "")
    print(f"Updated: {page_id}")
    print(f"URL: {url}")


@app.command()
def search(
    assignee: Annotated[str | None, typer.Option(help="Filter by assignee name")] = None,
    status: Annotated[str | None, typer.Option(help="Filter by status (e.g. 'In progress', 'Done')")] = None,
    query: Annotated[str | None, typer.Option(help="Search by title")] = None,
    since: SinceOption = None,
    limit: Annotated[int, typer.Option(help="Max results to display (0 for all)")] = 50,
    project: Annotated[str | None, typer.Option(help="Project key")] = None,
) -> None:
    """Search tickets."""
    config = get_config()
    queries = _build_ticket_queries(config, project=project, assignee=assignee, status=status, query=query, since=since)

    tickets: list[Ticket] = []
    for _name, database_id, body in queries:
        for page in _query_database(database_id, body):
            tickets.append(Ticket.from_page(page))

    if not tickets:
        print("No tickets found.")
        return

    tickets.sort(key=lambda t: t.resolve_date(), reverse=True)

    total = len(tickets)
    display_tickets = tickets if limit == 0 else tickets[:limit]
    truncated = limit > 0 and total > limit

    print(f"Found {total} ticket(s):\n")
    for t in display_tickets:
        print(t.display())
        print()

    if truncated:
        print(f"Showing {limit} of {total} ticket(s). Use --limit to see more.")


@app.command()
def stale(
    assignee: Annotated[str | None, typer.Option(help="Filter by assignee name")] = None,
    since: SinceOption = None,
    limit: Annotated[int, typer.Option(help="Max results to display (0 for all)")] = 50,
    project: Annotated[str | None, typer.Option(help="Project key")] = None,
) -> None:
    """List stale tickets (no status or no AH)."""
    config = get_config()
    queries = _build_ticket_queries(config, project=project, assignee=assignee, since=since)

    all_tickets: list[Ticket] = []
    for _name, database_id, body in queries:
        for page in _query_database(database_id, body):
            all_tickets.append(Ticket.from_page(page))

    stale_tickets: list[tuple[Ticket, str]] = []
    for t in all_tickets:
        reasons: list[str] = []
        if not t.status:
            reasons.append("no status")
        if t.ah is None:
            reasons.append("no AH")
        if reasons:
            stale_tickets.append((t, ", ".join(reasons)))

    stale_tickets.sort(key=lambda pair: pair[0].resolve_date(), reverse=True)

    if not stale_tickets:
        print("No stale tickets found.")
        return

    total = len(stale_tickets)
    display_stale = stale_tickets if limit == 0 else stale_tickets[:limit]
    truncated = limit > 0 and total > limit

    print(f"Found {total} stale ticket(s):\n")
    for t, reason in display_stale:
        print(t.display(reason=reason))
        print()

    if truncated:
        print(f"Showing {limit} of {total} stale ticket(s). Use --limit to see more.")


@app.command()
def epics(
    status: Annotated[str | None, typer.Option(help="Filter by status (e.g. 'In progress', 'Done')")] = None,
    project: Annotated[str | None, typer.Option(help="Project key")] = None,
) -> None:
    """List epics."""
    config = get_config()

    if project:
        proj_items = [(project, get_project_config(config, project))]
    else:
        proj_items = list(config.projects.items())

    all_results: list[dict[str, Any]] = []
    for _name, proj in proj_items:
        epics_db = proj.epics_database_id
        if not epics_db:
            continue

        status_type = proj.epic_status_type

        body: dict[str, Any] = {"page_size": 100}
        if status:
            body["filter"] = {
                "property": "Status",
                status_type: {"equals": status},
            }

        all_results.extend(_query_database(epics_db, body))

    if not all_results:
        print("No epics found.")
        return

    print(f"Found {len(all_results)} epic(s):\n")
    for page in all_results:
        e = Epic.from_page(page)
        print(e.display())
        print()


@app.command()
def report(
    period: Annotated[Period, typer.Option(help="Group by week or month")] = Period.WEEKLY,
    assignee: Annotated[str | None, typer.Option(help="Filter by assignee name")] = None,
    since: SinceOption = None,
    project: Annotated[str | None, typer.Option(help="Project key")] = None,
) -> None:
    """AH report grouped by week or month."""
    config = get_config()
    queries = _build_ticket_queries(config, project=project, assignee=assignee, since=since)

    results: list[dict[str, Any]] = []
    proj_names: list[str] = []
    for name, database_id, body in queries:
        results.extend(_query_database(database_id, body))
        proj_names.append(name)

    proj_name = ", ".join(proj_names)

    buckets: dict[str, list[float]] = {}

    for page in results:
        t = Ticket.from_page(page)
        if t.ah is None or t.ah <= 0:
            continue
        date_str = t.resolve_date()
        if not date_str:
            continue
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        if period == Period.MONTHLY:
            key = dt.strftime("%Y-%m")
        else:
            iso = dt.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"

        buckets.setdefault(key, []).append(t.ah)

    if not buckets:
        print("No tickets with AH found.")
        return

    sorted_keys = sorted(buckets.keys(), reverse=True)
    total_tickets = 0
    total_ah = 0.0

    print(f"AH Report ({period.value}) — {proj_name}\n")
    print(f"{'Period':<12} {'Tickets':>7}  {'Total AH':>8}  {'Avg AH':>6}")
    for key in sorted_keys:
        values = buckets[key]
        count = len(values)
        s = sum(values)
        avg = s / count
        total_tickets += count
        total_ah += s
        print(f"{key:<12} {count:>7}  {s:>8.0f}  {avg:>6.1f}")

    overall_avg = total_ah / total_tickets if total_tickets else 0
    print(f"\nSummary: {total_tickets} tickets, {total_ah:.0f} AH total, {overall_avg:.1f} avg")


@app.command("get-ticket")
def get_ticket(
    ticket: Annotated[str, typer.Argument(help="Ticket ID (e.g. GB-319) or Notion page-id")],
    project: Annotated[str | None, typer.Option(help="Project key")] = None,
) -> None:
    """Get full detail for a single ticket by ID or page-id."""
    config = get_config()

    match = re.match(r"^([A-Za-z]+)-(\d+)$", ticket)

    if match:
        # Human-readable ticket ID like GB-319
        number = int(match.group(2))
        body: dict[str, Any] = {
            "filter": {
                "property": "ID",
                "unique_id": {"equals": number},
            },
        }

        # Determine which projects to search
        if project:
            search_projects = [get_project_config(config, project)]
        else:
            search_projects = list(config.projects.values())

        page: dict[str, Any] | None = None
        for proj in search_projects:
            results = _query_database(proj.database_id, body)
            if results:
                # Verify prefix matches the ticket ID
                found_ticket = Ticket.from_page(results[0])
                if found_ticket.ticket_id and found_ticket.ticket_id.upper() == ticket.upper():
                    page = results[0]
                    break
        if not page:
            print(f"No ticket found matching '{ticket}'.", file=sys.stderr)
            raise typer.Exit(1)
    else:
        # Treat as page-id
        page = _get(f"/pages/{ticket}")

    t = Ticket.from_page(page)
    print(t.display(show_type=True))

    # Read page content (children blocks) as description
    content = _read_page_content(t.page_id)
    if content.strip():
        print()
        print("  Description:")
        for line in content.splitlines():
            print(f"    {line}")


@app.command()
def users() -> None:
    """Discover workspace users."""
    config = get_config()

    # Paginated user list
    found_users: dict[str, str] = {}
    start_cursor: str | None = None
    has_more = True

    while has_more:
        path = "/users"
        if start_cursor:
            path += f"?start_cursor={start_cursor}"
        resp = _get(path)

        for user in resp.get("results", []):
            if user.get("type") != "person":
                continue
            name = user.get("name", "")
            user_id = user.get("id", "")
            if name and user_id:
                found_users[name.lower()] = user_id

        has_more = resp.get("has_more", False)
        start_cursor = resp.get("next_cursor")

    if not found_users:
        print("No users found.")
        return

    print(f"Found {len(found_users)} user(s):\n")
    for name, uid in sorted(found_users.items()):
        # Mark users already in config
        marker = " (in config)" if name in config.users else ""
        print(f"  {name}: {uid}{marker}")

    # Offer to update config
    new_users = {k: v for k, v in found_users.items() if k not in config.users}
    if new_users:
        print(f"\n{len(new_users)} new user(s) not in config.")
        print("Add --save to update config file (not yet implemented).")


if __name__ == "__main__":
    app()
