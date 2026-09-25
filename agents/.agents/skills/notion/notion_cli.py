#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["typer", "pydantic", "pyyaml", "certifi", "rich"]
# ///
"""Notion CLI for ticket and epic management.

Standalone CLI that wraps the Notion API for creating, updating,
and searching tickets and epics. Uses typer for CLI, pydantic for
models, and stdlib urllib for HTTP.

Environment:
    NOTION_TOKEN: Required. Notion integration token.

Config:
    Reads from the skill-local notion.yaml, then ./config/notion.yaml.
    Override with --config flag.
"""

from __future__ import annotations

import contextlib
import csv
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal, cast

import certifi
import typer
import yaml
from pydantic import BaseModel, ConfigDict
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    TextColumn,
    TimeElapsedColumn,
)

# =============================================================================
# Constants
# =============================================================================

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
DATA_SOURCE_NOTION_VERSION = "2026-03-11"
SSL_CTX = ssl.create_default_context(cafile=certifi.where())

DEFAULT_CONFIG_PATHS = [
    Path(__file__).resolve().parent / "notion.yaml",
    Path("./config/notion.yaml"),
]

GITLAB_API_URL = "https://git.urieljsc.com/api/v4"
GITLAB_REPOS_PATH = Path.home() / ".agents" / "skills" / "gitlab" / "repos.yaml"

AH_WEEK_CSV_COLUMNS = ["id", "name", "status", "priority", "ah", "mr", "sort_date", "notion_url"]
AH_WEEK_EDITABLE_FIELDS = ("status", "priority", "ah", "mr")


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
    CLOSED = "Closed"


class Period(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# =============================================================================
# Pydantic Models
# =============================================================================


class ProjectConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")  # pyright: ignore[reportUnannotatedClassAttribute]

    database_id: str
    tickets_data_source_id: str = ""
    sprints_data_source_id: str = ""
    epics_database_id: str = ""
    prop_epic: str = "Epic"
    prop_epic_id: str = ""
    prop_sprint: str = "Sprint"
    prop_sprint_id: str = ""
    prop_sprint_date: str = "Start Date"
    prop_title_id: str = ""
    prop_assignee_id: str = ""
    prop_priority_id: str = ""
    prop_status_id: str = ""
    ticket_status_type: Literal["select", "status"] = "status"
    status_name_overrides: dict[str, str] = {}
    epic_status_type: Literal["select", "status"] = "select"
    date_property: str = "Sort Date"
    date_property_type: str = "formula"


class Config(BaseModel):
    model_config = ConfigDict(extra="ignore")  # pyright: ignore[reportUnannotatedClassAttribute]

    default_project: str = ""
    default_creator_alias: str = ""
    projects: dict[str, ProjectConfig] = {}
    users: dict[str, str] = {}


_EPOCH_PREFIX = "1970-01-01"
REPORT_DATE_PROPERTY = "Due Date"


class Ticket(BaseModel):
    ticket_id: str = ""
    name: str = ""
    status: str = ""
    priority: str = ""
    assignee: str = ""
    ah: float | None = None
    due_date: str = ""
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
            due_date=_read_date(props, REPORT_DATE_PROPERTY),
            sort_date=_read_formula_date(props, "Sort Date"),
            created=_read_timestamp(props, "Created time"),
            edited=_read_timestamp(props, "Last edited time"),
            gitlab_mr=_read_url(props, "Gitlab MR"),
            url=page.get("url", ""),
            page_id=page.get("id", ""),
            type_=_read_select(props, "Type"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Flat dict for machine-readable output."""
        return {
            "id": self.ticket_id,
            "name": self.name,
            "status": self.status,
            "priority": self.priority,
            "assignee": self.assignee,
            "ah": self.ah,
            "due_date": self.due_date or None,
            "sort_date": self.sort_date or None,
            "created": self.created or None,
            "edited": self.edited or None,
            "gitlab_mr": self.gitlab_mr or None,
            "url": self.url,
            "page_id": self.page_id,
            "type": self.type_ or None,
        }

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

    def resolve_report_date(self) -> str:
        """AH report date: due_date only."""
        dd = self.due_date
        if dd and not dd.startswith(_EPOCH_PREFIX):
            return dd
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


def _ticket_status_name(proj: ProjectConfig, status: Status | str) -> str:
    """Resolve a CLI status to the selected project's Notion option name."""
    name = status.value if isinstance(status, Status) else status
    return proj.status_name_overrides.get(name, name)


# =============================================================================
# HTTP helpers
# =============================================================================


def _headers(notion_version: str = NOTION_VERSION) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_token}",
        "Notion-Version": notion_version,
        "Content-Type": "application/json",
    }


def _request(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    notion_version: str = NOTION_VERSION,
) -> dict[str, Any]:
    """Make a Notion API request."""
    url = f"{NOTION_API_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, headers=_headers(notion_version), method=method)

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


def _post(path: str, body: dict[str, Any], notion_version: str = NOTION_VERSION) -> dict[str, Any]:
    return _request("POST", path, body, notion_version)


def _patch(path: str, body: dict[str, Any]) -> dict[str, Any]:
    return _request("PATCH", path, body)


def _get(path: str) -> dict[str, Any]:
    return _request("GET", path)


def _get_database_properties(database_id: str) -> dict[str, Any]:
    database = _get(f"/databases/{database_id}")
    props = database.get("properties")
    return cast(dict[str, Any], props) if isinstance(props, dict) else {}


def _create_property_keys(proj: ProjectConfig) -> tuple[str, str, str, str, str, str]:
    if not proj.tickets_data_source_id:
        return ("Name", "Assignee", proj.prop_sprint, proj.prop_epic, "Priority", "Status")

    required = {
        "prop_title_id": proj.prop_title_id,
        "prop_assignee_id": proj.prop_assignee_id,
        "prop_sprint_id": proj.prop_sprint_id,
        "prop_epic_id": proj.prop_epic_id,
        "prop_priority_id": proj.prop_priority_id,
        "prop_status_id": proj.prop_status_id,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        print(f"Error: project is missing create property id(s): {', '.join(missing)}", file=sys.stderr)
        raise typer.Exit(1)
    return (
        proj.prop_title_id,
        proj.prop_assignee_id,
        proj.prop_sprint_id,
        proj.prop_epic_id,
        proj.prop_priority_id,
        proj.prop_status_id,
    )


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


def _read_date(props: dict[str, Any], key: str) -> str:
    """Read a Notion date property."""
    raw_prop = props.get(key, {})
    raw = cast(dict[str, Any], raw_prop) if isinstance(raw_prop, dict) else {}
    date_value = raw.get("date")
    if isinstance(date_value, dict):
        date_dict = cast(dict[str, object], date_value)
        start = date_dict.get("start")
        return start if isinstance(start, str) else ""
    return ""


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


def _query_data_source(data_source_id: str, body: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Query a Notion data source, handling pagination."""
    payload = dict(body) if body else {}
    all_results: list[dict[str, Any]] = []
    has_more = True
    while has_more:
        resp = _request("POST", f"/data_sources/{data_source_id}/query", payload, DATA_SOURCE_NOTION_VERSION)
        all_results.extend(resp.get("results", []))
        has_more = resp.get("has_more", False)
        next_cursor = resp.get("next_cursor")
        if has_more and next_cursor:
            payload["start_cursor"] = next_cursor
        else:
            has_more = False
    return all_results


def _find_current_sprint_id(proj: ProjectConfig, today: date | None = None) -> str:
    """Find the latest sprint whose configured start date is on or before today."""
    if not proj.sprints_data_source_id:
        print("Error: project is missing sprints_data_source_id", file=sys.stderr)
        raise typer.Exit(1)

    current_date = today or date.today()
    body: dict[str, Any] = {
        "page_size": 1,
        "filter": {"property": proj.prop_sprint_date, "date": {"on_or_before": current_date.isoformat()}},
        "sorts": [{"property": proj.prop_sprint_date, "direction": "descending"}],
    }
    results = _query_data_source(proj.sprints_data_source_id, body)
    if not results:
        print(
            f"Error: no current sprint found with {proj.prop_sprint_date} on or before {current_date.isoformat()}",
            file=sys.stderr,
        )
        raise typer.Exit(1)

    sprint_id = str(results[0].get("id", ""))
    if not sprint_id:
        print("Error: current sprint result did not include a page ID", file=sys.stderr)
        raise typer.Exit(1)
    return sprint_id


def _build_filter_body(
    config: Config,
    assignee: str | None = None,
    status: str | None = None,
    query: str | None = None,
    since: date | None = None,
    proj: ProjectConfig | None = None,
    date_property: str | None = None,
    date_property_type: str | None = None,
) -> dict[str, Any]:
    """Build filter and sort body for ticket queries.

    Uses project-level ``date_property`` (default: ``Sort Date``) for
    ``--since`` filtering and sort ordering.  The property type defaults to
    ``formula`` but can be overridden per project via ``date_property_type``
    (e.g. ``created_time``).
    """
    date_prop = date_property or (proj.date_property if proj else "Sort Date")
    date_type = date_property_type or (proj.date_property_type if proj else "formula")

    filters: list[dict[str, Any]] = []
    if assignee:
        user_id = resolve_user_id(config, assignee)
        if not user_id:
            available = ", ".join(sorted(config.users.keys()))
            print(f"Error: unknown assignee '{assignee}'. Available: {available}", file=sys.stderr)
            sys.exit(1)
        filters.append({"property": "Assignee", "people": {"contains": user_id}})
    if status:
        status_type = proj.ticket_status_type if proj else "status"
        status_name = _ticket_status_name(proj, status) if proj else status
        filters.append({"property": "Status", status_type: {"equals": status_name}})
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
    date_property: str | None = None,
    date_property_type: str | None = None,
) -> list[tuple[str, str, dict[str, Any]]]:
    """Build ticket queries across projects.

    When --project is specified, queries that project only.
    When omitted, queries ALL configured projects.

    Returns list of (project_name, database_id, query_body).
    """
    if project:
        proj = get_project_config(config, project)
        body = _build_filter_body(
            config,
            assignee=assignee,
            status=status,
            query=query,
            since=since,
            proj=proj,
            date_property=date_property,
            date_property_type=date_property_type,
        )
        return [(project, proj.database_id, body)]

    result: list[tuple[str, str, dict[str, Any]]] = []
    for name, proj in config.projects.items():
        body = _build_filter_body(
            config,
            assignee=assignee,
            status=status,
            query=query,
            since=since,
            proj=proj,
            date_property=date_property,
            date_property_type=date_property_type,
        )
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
# AH week helpers (weekly CSV reconciliation)
# =============================================================================


def _ah_week_progress(enabled: bool) -> Progress | contextlib.nullcontext:
    """Transient stderr progress bar for interactive terminals; no-op otherwise."""
    if not enabled:
        return contextlib.nullcontext()
    return Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=Console(stderr=True),
        transient=True,
    )


def _ah_week_range(since: date | None, until: date | None, today: date | None = None) -> tuple[date, date]:
    """Resolve the week window: Mon-Sun containing today, or explicit since/until."""
    # Wall-clock default is intentional: the week window follows the local week.
    day = today or date.today()  # noqa: DTZ011
    if since is None and until is None:
        monday = day - timedelta(days=day.weekday())
        return monday, monday + timedelta(days=6)
    start = since or day
    end = until or day
    if end < start:
        print("Error: --until is before --since", file=sys.stderr)
        raise typer.Exit(1)
    return start, end


def _build_mr_index(mrs: list[dict[str, Any]]) -> dict[str, str]:
    """Map ticket ids found in MR titles to the best MR web_url.

    Prefers state merged > opened > other; on ties the most recent updated_at wins.
    """
    best: dict[str, tuple[int, str, str]] = {}
    for mr in mrs:
        url = mr.get("web_url", "")
        if not url:
            continue
        rank = {"merged": 2, "opened": 1}.get(mr.get("state", ""), 0)
        updated = mr.get("updated_at", "")
        for tid in re.findall(r"\b([A-Za-z]+-\d+)\b", mr.get("title", "")):
            cur = best.get(tid)
            if cur is None or rank > cur[0] or (rank == cur[0] and updated > cur[2]):
                best[tid] = (rank, url, updated)
    return {tid: url for tid, (_rank, url, _updated) in best.items()}


def _gitlab_repos() -> list[str]:
    """Read the GitLab repo list from the gitlab skill's repos.yaml."""
    try:
        raw = yaml.safe_load(GITLAB_REPOS_PATH.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return []
    repos = raw.get("repos")
    return [str(r) for r in repos] if isinstance(repos, list) else []


def _gitlab_get_json(path: str, token: str) -> Any:
    req = urllib.request.Request(f"{GITLAB_API_URL}{path}", headers={"PRIVATE-TOKEN": token})
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=30) as resp:
        return json.loads(resp.read())


def _ah_week_fetch_project(
    name: str, proj: ProjectConfig, body: dict[str, Any], start_str: str, end_str: str
) -> tuple[str, list[dict[str, str]]]:
    """Fetch one project's tickets (full pagination) and filter to the week, client-side."""
    rows: list[dict[str, str]] = []
    for page in _query_database(proj.database_id, body):
        t = Ticket.from_page(page)
        sd = (t.sort_date or "")[:10]
        if not sd or sd.startswith(_EPOCH_PREFIX) or not (start_str <= sd <= end_str):
            continue
        rows.append(
            {
                "id": t.ticket_id or t.page_id[:8],
                "name": t.name,
                "status": t.status,
                "priority": t.priority,
                "ah": str(t.ah) if t.ah is not None else "",
                "mr": t.gitlab_mr,
                "sort_date": sd,
                "notion_url": t.url,
                "project": name,
            }
        )
    return name, rows


def _ah_week_fetch_repo_mrs(repo: str, token: str) -> tuple[str, list[dict[str, Any]]]:
    """Fetch all MRs (every state) from one repo. Errors skip the repo with a warning."""
    mrs: list[dict[str, Any]] = []
    page_no = 1
    while True:
        encoded = urllib.parse.quote(repo, safe="")
        path = f"/projects/{encoded}/merge_requests?state=all&per_page=100&order_by=updated_at&page={page_no}"
        try:
            batch = _gitlab_get_json(path, token)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            print(f"Warning: GitLab fetch failed for {repo}: {e}", file=sys.stderr)
            break
        if not isinstance(batch, list) or not batch:
            break
        mrs.extend(batch)
        if len(batch) < 100:
            break
        page_no += 1
    return repo, mrs


def _fetch_gitlab_mrs(repos: list[str], token: str, max_workers: int = 8) -> list[dict[str, Any]]:
    """Fetch all MRs concurrently from the configured repos. Errors skip a repo."""
    mrs: list[dict[str, Any]] = []
    if not repos:
        return mrs
    with ThreadPoolExecutor(max_workers=min(max_workers, len(repos))) as pool:
        futures = [pool.submit(_ah_week_fetch_repo_mrs, repo, token) for repo in repos]
        for future in as_completed(futures):
            _repo, repo_mrs = future.result()
            mrs.extend(repo_mrs)
    return mrs


def _ah_baseline_path(csv_path: Path) -> Path:
    return Path(str(csv_path) + ".baseline")


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with open(path, newline="") as f:
        rows: list[dict[str, str]] = []
        for row in csv.DictReader(f):
            clean = {k: (v or "") for k, v in row.items() if k is not None}
            tid = clean.get("id", "")
            if not tid:
                print(f"Warning: {path.name}: skipping row without an id", file=sys.stderr)
                continue
            if any(r["id"] == tid for r in rows):
                print(f"Warning: {path.name}: duplicate id {tid}; keeping the first row", file=sys.stderr)
                continue
            rows.append(clean)
    return rows


def _write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _ah_week_merge(
    pulled: list[dict[str, str]], csv_path: Path, baseline_path: Path, scan_skipped: bool = False
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Merge freshly pulled rows with an existing edited CSV.

    The baseline rows carry an extra `project` column used by --apply.
    Only the editable fields count as user edits (other columns always
    refresh from the pull). Keeps rows the pull no longer returned.
    When scan_skipped is set, an empty pulled MR does not overwrite an
    existing non-empty MR (the GitLab scan may simply not have run).
    Returns (csv_rows, baseline_rows), both sorted by id.
    """
    pulled_by_id = {r["id"]: r for r in pulled}
    existing: dict[str, dict[str, str]] = {}
    old_base: dict[str, dict[str, str]] = {}
    if csv_path.exists() and baseline_path.exists():
        existing = {r["id"]: r for r in _read_csv_rows(csv_path)}
        old_base = {r["id"]: r for r in _read_csv_rows(baseline_path)}

    csv_rows: list[dict[str, str]] = []
    base_rows: list[dict[str, str]] = []
    for tid in sorted(set(pulled_by_id) | set(existing)):
        p = pulled_by_id.get(tid)
        cur = existing.get(tid)
        base = old_base.get(tid)
        if p is not None and cur is not None and base is not None:
            merged: dict[str, str] = {}
            for f in AH_WEEK_CSV_COLUMNS:
                if f in AH_WEEK_EDITABLE_FIELDS and cur.get(f, "") != base.get(f, ""):
                    merged[f] = cur[f]
                else:
                    merged[f] = p.get(f, "")
            if scan_skipped and not merged["mr"] and cur.get("mr"):
                merged["mr"] = cur["mr"]
            # Baseline: pulled values for refreshed fields, but the old baseline value
            # where the user edited, so --diff still shows the pending edit.
            base_row = {
                f: (base[f] if f in AH_WEEK_EDITABLE_FIELDS and cur.get(f, "") != base.get(f, "") else p.get(f, ""))
                for f in AH_WEEK_CSV_COLUMNS
            }
            base_row["mr"] = merged["mr"]
            base_row["project"] = p.get("project", "")
            csv_rows.append(merged)
            base_rows.append(base_row)
        elif p is not None:
            # New ticket row: pulled values everywhere.
            row = {f: p.get(f, "") for f in AH_WEEK_CSV_COLUMNS}
            csv_rows.append(row)
            base_rows.append(dict(row) | {"project": p.get("project", "")})
        else:
            # Pull no longer returned this row: keep user data untouched.
            if cur is not None:
                csv_rows.append({f: cur.get(f, "") for f in AH_WEEK_CSV_COLUMNS})
            if base is not None:
                base_rows.append({f: base.get(f, "") for f in AH_WEEK_CSV_COLUMNS} | {"project": base.get("project", "")})
    return csv_rows, base_rows


def _ah_week_changes(csv_path: Path, baseline_path: Path) -> dict[str, dict[str, tuple[str, str]]]:
    """Diff the edited CSV against its baseline on the editable fields."""
    csv_rows = {r["id"]: r for r in _read_csv_rows(csv_path)}
    base_rows = {r["id"]: r for r in _read_csv_rows(baseline_path)}
    changes: dict[str, dict[str, tuple[str, str]]] = {}
    for tid in sorted(set(csv_rows) | set(base_rows)):
        cur = csv_rows.get(tid)
        old = base_rows.get(tid)
        if cur is None or old is None:
            continue
        fields: dict[str, tuple[str, str]] = {}
        for f in AH_WEEK_EDITABLE_FIELDS:
            if cur.get(f, "") != old.get(f, ""):
                fields[f] = (old.get(f, ""), cur.get(f, ""))
        if fields:
            changes[tid] = fields
    return changes


def _ah_week_removed_ids(csv_path: Path, baseline_path: Path) -> list[str]:
    csv_ids = {r["id"] for r in _read_csv_rows(csv_path)}
    base_ids = {r["id"] for r in _read_csv_rows(baseline_path)}
    return sorted(base_ids - csv_ids)


def _ah_week_added_ids(csv_path: Path, baseline_path: Path) -> list[str]:
    csv_ids = {r["id"] for r in _read_csv_rows(csv_path)}
    base_ids = {r["id"] for r in _read_csv_rows(baseline_path)}
    return sorted(csv_ids - base_ids)


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
UntilOption = Annotated[date | None, typer.Option(help="End of window YYYY-MM-DD", parser=_parse_since)]
ReportSinceOption = Annotated[date | None, typer.Option(help="Filter by Due Date >= YYYY-MM-DD", parser=_parse_since)]


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
    epic: Annotated[str, typer.Option(help="Epic name to link")],
    description: Annotated[str, typer.Option(help="Ticket description (markdown)")] = "",
    priority: Annotated[Priority, typer.Option(help="Ticket priority")] = Priority.MEDIUM,
    status: Annotated[Status | None, typer.Option(help="Ticket status")] = None,
    assignee: Annotated[str | None, typer.Option(help="Assignee name (from config users)")] = None,
    project: Annotated[str | None, typer.Option(help="Project key")] = None,
) -> None:
    """Create a ticket."""
    config = get_config()
    proj = get_project_config(config, project)
    assignee_name = assignee or config.default_creator_alias
    if not assignee_name:
        print("Error: missing default_creator_alias in config; pass --assignee or configure a default", file=sys.stderr)
        raise typer.Exit(1)
    user_id = resolve_user_id(config, assignee_name)
    if not user_id:
        available = ", ".join(sorted(config.users.keys()))
        print(f"Error: unknown assignee '{assignee_name}'. Available: {available}", file=sys.stderr)
        raise typer.Exit(1)
    epic_name = epic.strip()
    epics_db = proj.epics_database_id
    if not epics_db:
        print("Error: selected project has no epics_database_id configured", file=sys.stderr)
        raise typer.Exit(1)
    epic_id = _find_epic_id(epics_db, epic_name)
    if not epic_id:
        print(f"Error: epic '{epic_name}' not found; run the epics command and pass an existing epic", file=sys.stderr)
        raise typer.Exit(1)
    sprint_id = _find_current_sprint_id(proj)
    title_key, assignee_key, sprint_key, epic_key, priority_key, status_key = _create_property_keys(proj)

    properties: dict[str, Any] = {
        title_key: {"title": [{"text": {"content": title}}]},
        assignee_key: {"people": [{"id": user_id}]},
        sprint_key: {"relation": [{"id": sprint_id}]},
        epic_key: {"relation": [{"id": epic_id}]},
    }

    properties[priority_key] = {"select": {"name": priority.value}}

    if status is not None:
        properties[status_key] = {
            proj.ticket_status_type: {"name": _ticket_status_name(proj, status)}
        }

    children = _markdown_to_blocks(description) if description else []

    parent = {"data_source_id": proj.tickets_data_source_id} if proj.tickets_data_source_id else {"database_id": proj.database_id}
    notion_version = DATA_SOURCE_NOTION_VERSION if proj.tickets_data_source_id else NOTION_VERSION
    payload: dict[str, Any] = {
        "parent": parent,
        "properties": properties,
    }
    if children:
        payload["children"] = children

    page = _post("/pages", payload, notion_version)

    page_id = page.get("id", "")
    url = page.get("url", "")
    props = page.get("properties", {})
    ticket_id = _read_unique_id(props)

    print(f"Created: {title}")
    if ticket_id:
        print(f"Ticket: {ticket_id}")
    print(f"ID: {page_id}")
    print(f"URL: {url}")


def _resolve_page(ticket: str, config: Config, project: str | None = None) -> dict[str, Any] | None:
    """Resolve a ticket ID (e.g. 'SN-319') or a page UUID to a page dict.

    Ticket IDs are looked up via the unique_id property across the selected
    project (or all projects when --project is omitted). A UUID is fetched
    directly. Returns None when a ticket ID matches nothing; callers decide
    how to report the miss.
    """
    match = re.match(r"^([A-Za-z]+)-(\d+)$", ticket)
    if not match:
        return _get(f"/pages/{ticket}")

    number = int(match.group(2))
    body: dict[str, Any] = {
        "filter": {"property": "ID", "unique_id": {"equals": number}},
    }
    if project:
        search_projects = [get_project_config(config, project)]
    else:
        search_projects = list(config.projects.values())

    for proj in search_projects:
        results = _query_database(proj.database_id, body)
        if results:
            found = Ticket.from_page(results[0])
            if found.ticket_id and found.ticket_id.upper() == ticket.upper():
                return results[0]

    return None


def _find_epic_id(epics_db: str, epic_name: str) -> str | None:
    """Search epics database for an epic by name using a title filter."""
    schema_props = _get_database_properties(epics_db)
    title_props: list[str] = []
    for prop_name in ("Epic", "Name"):
        raw = schema_props.get(prop_name)
        prop = cast(dict[str, Any], raw) if isinstance(raw, dict) else {}
        if prop.get("type") == "title":
            title_props.append(prop_name)
    if not title_props:
        return None

    filters = [{"property": prop_name, "title": {"equals": epic_name}} for prop_name in title_props]
    body: dict[str, Any] = {
        "filter": filters[0] if len(filters) == 1 else {"or": filters}
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
    page_id: Annotated[str, typer.Option(help="Ticket ID (e.g. GB-319) or Notion page UUID")],
    title: Annotated[str | None, typer.Option(help="New title")] = None,
    status: Annotated[Status | None, typer.Option(help="New status")] = None,
    priority: Annotated[Priority | None, typer.Option(help="New priority")] = None,
    assignee: Annotated[str | None, typer.Option(help="New assignee name")] = None,
    epic: Annotated[str | None, typer.Option(help="Epic name to link")] = None,
    ah: Annotated[float | None, typer.Option(help="Actual working hours")] = None,
    description: Annotated[str | None, typer.Option(help="New description (replaces existing)")] = None,
    project: Annotated[str | None, typer.Option(help="Project key")] = None,
) -> None:
    """Update a ticket."""
    config = get_config()
    resolved = _resolve_page(page_id, config, project)
    if resolved is None:
        print(f"No ticket found matching '{page_id}'.", file=sys.stderr)
        raise typer.Exit(1)
    page_id = resolved["id"]
    properties = _build_update_properties(config, project, title, status, priority, assignee, epic, ah)

    if not properties and not description:
        print("Error: nothing to update. Provide at least one field.", file=sys.stderr)
        raise typer.Exit(1)

    if properties:
        page = _patch(f"/pages/{page_id}", {"properties": properties})
    else:
        page = _get(f"/pages/{page_id}")

    if description:
        _replace_page_blocks(page_id, _markdown_to_blocks(description))

    props = page.get("properties", {})
    ticket_id = _read_unique_id(props)
    title = _read_title(props)
    url = page.get("url", "")
    print(f"Updated: {ticket_id or title}")
    print(f"ID: {page.get('id', '')}")
    print(f"URL: {url}")


def _build_update_properties(
    config: Config,
    project: str | None,
    title: str | None,
    status: Status | None,
    priority: Priority | None,
    assignee: str | None,
    epic: str | None,
    ah: float | None,
) -> dict[str, Any]:
    """Build a Notion properties payload from bulk/update field options."""
    properties: dict[str, Any] = {}
    if title:
        properties["Name"] = {"title": [{"text": {"content": title}}]}
    if status is not None:
        status_proj = get_project_config(config, project) if project or config.default_project in config.projects else None
        status_type = status_proj.ticket_status_type if status_proj else "status"
        status_name = _ticket_status_name(status_proj, status) if status_proj else status.value
        properties["Status"] = {status_type: {"name": status_name}}
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
    if epic:
        proj = get_project_config(config, project)
        epics_db = proj.epics_database_id
        if not epics_db:
            print("Error: selected project has no epics_database_id configured", file=sys.stderr)
            raise typer.Exit(1)
        epic_id = _find_epic_id(epics_db, epic.strip())
        if not epic_id:
            print(f"Error: epic '{epic}' not found; run the epics command and pass an existing epic", file=sys.stderr)
            raise typer.Exit(1)
        properties[proj.prop_epic] = {"relation": [{"id": epic_id}]}
    return properties


@app.command()
def bulk(
    tickets: Annotated[list[str], typer.Argument(help="Ticket IDs (e.g. SN-199 SN-200) or page UUIDs")],
    title: Annotated[str | None, typer.Option(help="New title (applied to every ticket)")] = None,
    status: Annotated[Status | None, typer.Option(help="New status")] = None,
    priority: Annotated[Priority | None, typer.Option(help="New priority")] = None,
    assignee: Annotated[str | None, typer.Option(help="New assignee name")] = None,
    epic: Annotated[str | None, typer.Option(help="Epic name to link")] = None,
    ah: Annotated[float | None, typer.Option(help="Actual working hours")] = None,
    project: Annotated[str | None, typer.Option(help="Project key")] = None,
) -> None:
    """Apply the same update to many tickets at once."""
    config = get_config()
    properties = _build_update_properties(config, project, title, status, priority, assignee, epic, ah)
    if not properties:
        print("Error: nothing to set. Provide at least one field.", file=sys.stderr)
        raise typer.Exit(1)

    failed = 0
    for ticket in tickets:
        resolved = _resolve_page(ticket, config, project)
        if resolved is None:
            print(f"FAIL {ticket}: not found")
            failed += 1
            continue
        _patch(f"/pages/{resolved['id']}", {"properties": properties})
        tid = _read_unique_id(resolved.get("properties", {}))
        print(f"OK   {tid or ticket}")

    total = len(tickets)
    print(f"\nUpdated {total - failed} of {total} ticket(s).")
    if failed:
        raise typer.Exit(1)


@app.command()
def search(
    assignee: Annotated[str | None, typer.Option(help="Filter by assignee name")] = None,
    status: Annotated[str | None, typer.Option(help="Filter by status (e.g. 'In progress', 'Done')")] = None,
    query: Annotated[str | None, typer.Option(help="Search by title")] = None,
    since: SinceOption = None,
    limit: Annotated[int, typer.Option(help="Max results to display (0 for all)")] = 50,
    project: Annotated[str | None, typer.Option(help="Project key")] = None,
    json_out: Annotated[bool, typer.Option("--json", help="Print machine-readable JSON array")] = False,
) -> None:
    """Search tickets."""
    config = get_config()
    queries = _build_ticket_queries(config, project=project, assignee=assignee, status=status, query=query, since=since)

    tickets: list[Ticket] = []
    for _name, database_id, body in queries:
        for page in _query_database(database_id, body):
            tickets.append(Ticket.from_page(page))

    tickets.sort(key=lambda t: t.resolve_date(), reverse=True)

    if json_out:
        display_tickets = tickets if limit == 0 else tickets[:limit]
        print(json.dumps([t.to_dict() for t in display_tickets], indent=2, ensure_ascii=False))
        return

    if not tickets:
        print("No tickets found.")
        return

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
    since: ReportSinceOption = None,
    project: Annotated[str | None, typer.Option(help="Project key")] = None,
) -> None:
    """AH report grouped by week or month using Due Date."""
    config = get_config()
    queries = _build_ticket_queries(
        config,
        project=project,
        assignee=assignee,
        since=since,
        date_property=REPORT_DATE_PROPERTY,
        date_property_type="date",
    )

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
        date_str = t.resolve_report_date()
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


@app.command("ah-week")
def ah_week(
    diff: Annotated[bool, typer.Option(help="Show changes vs the baseline snapshot")] = False,
    report: Annotated[bool, typer.Option(help="Print AH totals from the CSV")] = False,
    apply: Annotated[bool, typer.Option(help="Push the diff to Notion and refresh the baseline")] = False,
    out: Annotated[str | None, typer.Option(help="CSV path (default: ah-week-<year>-W<week>.csv)")] = None,
    assignee: Annotated[str | None, typer.Option(help="Assignee name (default: default_creator_alias)")] = None,
    since: SinceOption = None,
    until: UntilOption = None,
) -> None:
    """Weekly ticket/AH reconciliation via a local CSV.

    Default: pull the week's tickets into a CSV plus a hidden .baseline
    snapshot. --diff shows edits vs baseline, --report prints AH totals,
    --apply pushes status/priority/AH changes to Notion.
    """
    config = get_config()
    start, end = _ah_week_range(since, until)
    iso = start.isocalendar()
    csv_path = Path(out) if out else Path(f"ah-week-{iso[0]}-W{iso[1]:02d}.csv")
    baseline_path = _ah_baseline_path(csv_path)

    if diff:
        for p in (csv_path, baseline_path):
            if not p.exists():
                print(f"Error: {p} not found. Run ah-week (pull) first.", file=sys.stderr)
                raise typer.Exit(1)
        for tid in _ah_week_added_ids(csv_path, baseline_path):
            print(f"added {tid}")
        for tid in _ah_week_removed_ids(csv_path, baseline_path):
            print(f"removed {tid} (not pushed; remove rows only in the CSV)")
        changes = _ah_week_changes(csv_path, baseline_path)
        for tid, fields in changes.items():
            for field, (old, new) in fields.items():
                print(f"{tid} {field}: {old or '(blank)'} -> {new or '(blank)'}")
        if not changes and not _ah_week_added_ids(csv_path, baseline_path) and not _ah_week_removed_ids(csv_path, baseline_path):
            print("No changes vs baseline.")
        return

    if report:
        if not csv_path.exists():
            print(f"Error: {csv_path} not found. Run ah-week (pull) first.", file=sys.stderr)
            raise typer.Exit(1)
        rows = _read_csv_rows(csv_path)
        ah: dict[str, float] = {}
        for r in rows:
            if not r.get("ah"):
                continue
            try:
                ah[r["id"]] = float(r["ah"])
            except ValueError:
                print(f"Warning: skipping non-numeric AH '{r['ah']}' for {r['id']}", file=sys.stderr)
        total = sum(ah.values())
        # Report the CSV's own date window when it has dates, so historical/custom
        # files are labelled correctly instead of the current week.
        csv_dates = sorted(r["sort_date"][:10] for r in rows if r.get("sort_date"))
        if csv_dates:
            start, end = date.fromisoformat(csv_dates[0]), date.fromisoformat(csv_dates[-1])
        days = (end - start).days + 1
        weekdays = sum(1 for i in range(days) if (start + timedelta(days=i)).weekday() < 5)
        by_project: dict[str, float] = {}
        by_status: dict[str, float] = {}
        for r in rows:
            if r["id"] not in ah:
                continue
            prefix = r["id"].rsplit("-", 1)[0]
            by_project[prefix] = by_project.get(prefix, 0.0) + ah[r["id"]]
            by_status[r.get("status") or "(no status)"] = by_status.get(r.get("status") or "(no status)", 0.0) + ah[r["id"]]
        print(f"AH Report {start} - {end} ({days} days)\n")
        print(f"Total AH: {total:.1f} across {len(ah)} of {len(rows)} ticket(s)")
        print(f"Avg per day: {total / days:.2f} (all days), {total / weekdays:.2f} ({weekdays} weekdays)")
        print("\nBy project:")
        for key in sorted(by_project):
            print(f"  {key}: {by_project[key]:.1f}")
        print("\nBy status:")
        for key in sorted(by_status):
            print(f"  {key}: {by_status[key]:.1f}")
        print("\nTickets with AH:")
        for r in rows:
            if r["id"] in ah:
                print(f"  {r['id']:<10} {r.get('status') or '(no status)':<12} {ah[r['id']]:>5.1f}")
        return

    # Pull (default) and apply both need the files.
    if apply:
        for p in (csv_path, baseline_path):
            if not p.exists():
                print(f"Error: {p} not found. Run ah-week (pull) first.", file=sys.stderr)
                raise typer.Exit(1)
        changes = _ah_week_changes(csv_path, baseline_path)
        if not changes:
            print("No changes vs baseline. Nothing to apply.")
            return
        base_rows = {r["id"]: r for r in _read_csv_rows(baseline_path)}
        csv_rows = {r["id"]: r for r in _read_csv_rows(csv_path)}
        failed = 0
        local_mr = 0
        local_only = 0
        print(f"Applying to Notion ({len(changes)} ticket(s))...")
        for tid, fields in changes.items():
            project = base_rows.get(tid, {}).get("project", "")
            properties: dict[str, Any] = {}
            if "status" in fields:
                new_status = fields["status"][1]
                if new_status:
                    properties["Status"] = new_status
            if "priority" in fields and fields["priority"][1]:
                try:
                    properties["Priority"] = {"select": {"name": Priority(fields["priority"][1]).value}}
                except ValueError:
                    print(f"FAIL {tid}: priority '{fields['priority'][1]}' is not Low/Medium/High/Critical")
                    failed += 1
                    continue
            if "ah" in fields and fields["ah"][1]:
                try:
                    properties["AH"] = {"number": float(fields["ah"][1])}
                except ValueError:
                    print(f"FAIL {tid}: ah '{fields['ah'][1]}' is not a number")
                    failed += 1
                    continue
            if "mr" in fields:
                local_mr += 1
            if not properties:
                local_only += 1
                continue
            # Status needs the project's option type + name mapping applied below.
            try:
                resolved = _resolve_page(tid, config, project or None)
            except SystemExit:
                # A UUID-style row id (ticket without unique_id) can 404 on a direct
                # fetch; count it as FAIL instead of killing the whole apply.
                print(f"FAIL {tid}: not found")
                failed += 1
                continue
            if resolved is None:
                print(f"FAIL {tid}: not found")
                failed += 1
                continue
            if "Status" in properties:
                proj = config.projects.get(project)
                if proj is None:
                    print(f"FAIL {tid}: unknown project for status update")
                    failed += 1
                    continue
                properties["Status"] = {proj.ticket_status_type: {"name": _ticket_status_name(proj, properties["Status"])}}
            _patch(f"/pages/{resolved['id']}", {"properties": properties})
            print(f"OK   {tid}")
        total = len(changes)
        applied = total - failed - local_only
        print(f"\nApplied {applied}, local-only {local_only}, failed {failed} of {total} ticket(s).")
        if local_mr:
            print(f"Local-only (not in Notion API): {local_mr} MR change(s) — kept in CSV/baseline only.")
        if failed:
            raise typer.Exit(1)
        refreshed = [{**csv_rows[tid], "project": base_rows.get(tid, {}).get("project", "")} for tid in sorted(csv_rows)]
        _write_csv(baseline_path, refreshed, AH_WEEK_CSV_COLUMNS + ["project"])
        return

    # Pull: fetch all tickets for the assignee across all projects, filter dates client-side.
    assignee_name = assignee or config.default_creator_alias
    if not assignee_name:
        print("Error: missing default_creator_alias in config; pass --assignee", file=sys.stderr)
        raise typer.Exit(1)
    user_id = resolve_user_id(config, assignee_name)
    if not user_id:
        available = ", ".join(sorted(config.users.keys()))
        print(f"Error: unknown assignee '{assignee_name}'. Available: {available}", file=sys.stderr)
        raise typer.Exit(1)

    body: dict[str, Any] = {
        "page_size": 100,
        "filter": {"property": "Assignee", "people": {"contains": user_id}},
        "sorts": [{"property": "Sort Date", "direction": "descending"}],
    }
    start_str, end_str = start.isoformat(), end.isoformat()

    # MR column: scan configured GitLab repos, fall back to Notion MR property.
    gitlab_token = os.environ.get("GITLAB_TOKEN", "")
    repos: list[str] = []
    scan_skipped = False
    if gitlab_token:
        repos = _gitlab_repos()
        if not repos:
            scan_skipped = True
            print(f"Warning: no GitLab repos found in {GITLAB_REPOS_PATH}; using Notion MR property only", file=sys.stderr)
    else:
        scan_skipped = True
        print("Warning: GITLAB_TOKEN not set; skipping GitLab MR scan, using Notion MR property only", file=sys.stderr)

    # Notion projects and GitLab repos are independent chains; fetch them all
    # concurrently (pages within a chain stay sequential for cursor pagination).
    work: list[tuple[str, Any]] = []
    for name, proj in config.projects.items():
        work.append((f"Notion: {name}", lambda n=name, p=proj: _ah_week_fetch_project(n, p, body, start_str, end_str)))
    for repo in repos:
        work.append((f"GitLab: {repo}", lambda r=repo: _ah_week_fetch_repo_mrs(r, gitlab_token)))

    interactive = sys.stderr.isatty()
    pulled: list[dict[str, str]] = []
    all_mrs: list[dict[str, Any]] = []
    with _ah_week_progress(interactive) as progress:
        task = progress.add_task("Fetching Notion + GitLab", total=len(work)) if interactive else None
        if not interactive:
            print(f"Fetching {len(config.projects)} Notion project(s) + {len(repos)} GitLab repo(s)...")
        with ThreadPoolExecutor(max_workers=min(12, max(4, len(work)))) as pool:
            futures = {pool.submit(fn): label for label, fn in work}
            for future in as_completed(futures):
                label = futures[future]
                name, payload = future.result()
                if label.startswith("Notion:"):
                    pulled.extend(payload)
                else:
                    all_mrs.extend(payload)
                if task is not None:
                    progress.update(task, advance=1, description=f"{label} done")
    if not scan_skipped:
        mr_index = _build_mr_index(all_mrs)
        for row in pulled:
            row["mr"] = mr_index.get(row["id"]) or row["mr"]

    csv_rows, base_rows = _ah_week_merge(pulled, csv_path, baseline_path, scan_skipped=scan_skipped)
    _write_csv(csv_path, csv_rows, AH_WEEK_CSV_COLUMNS)
    _write_csv(baseline_path, base_rows, AH_WEEK_CSV_COLUMNS + ["project"])
    print(f"Pulled {len(pulled)} ticket(s) for {start} - {end} into {csv_path}.")
    print(f"Baseline: {baseline_path}")


@app.command("get-ticket")
def get_ticket(
    ticket: Annotated[str, typer.Argument(help="Ticket ID (e.g. GB-319) or Notion page-id")],
    project: Annotated[str | None, typer.Option(help="Project key")] = None,
) -> None:
    """Get full detail for a single ticket by ID or page-id."""
    config = get_config()
    page = _resolve_page(ticket, config, project)
    if page is None:
        print(f"No ticket found matching '{ticket}'.", file=sys.stderr)
        raise typer.Exit(1)

    t = Ticket.from_page(page)
    print(t.display(show_type=True))
    print(f"    ID: {t.page_id}")

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
