#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml", "certifi"]
# ///
"""Notion CLI for ticket and epic management.

Standalone CLI that wraps the Notion API for creating, updating,
and searching tickets and epics. Uses stdlib urllib + PyYAML only.

Environment:
    NOTION_TOKEN: Required. Notion integration token.

Config:
    Reads from ./config/notion.yaml or ~/Source/claude-boy/config/notion.yaml.
    Override with --config flag.
"""

import argparse
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import certifi
import yaml

SSL_CTX = ssl.create_default_context(cafile=certifi.where())

NOTION_API_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

DEFAULT_CONFIG_PATHS = [
    Path("./config/notion.yaml"),
    Path.home() / "Source" / "claude-boy" / "config" / "notion.yaml",
]


# =============================================================================
# Config
# =============================================================================


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """Load config from YAML file."""
    if config_path:
        p = Path(config_path)
        if not p.exists():
            print(f"Error: config not found at {p}", file=sys.stderr)
            sys.exit(1)
        with open(p) as f:
            return yaml.safe_load(f) or {}

    for p in DEFAULT_CONFIG_PATHS:
        if p.exists():
            with open(p) as f:
                return yaml.safe_load(f) or {}

    return {}


def get_project_config(config: dict[str, Any], project: str | None = None) -> dict[str, Any]:
    """Get project-specific config."""
    projects = config.get("projects", {})
    key = project or config.get("default_project", "")
    if key not in projects:
        available = ", ".join(projects.keys())
        print(f"Error: unknown project '{key}'. Available: {available}", file=sys.stderr)
        sys.exit(1)
    return projects[key]


def resolve_user_id(config: dict[str, Any], name: str) -> str | None:
    """Look up user ID by name (case-insensitive)."""
    users = config.get("users", {})
    return users.get(name.lower())


# =============================================================================
# HTTP helpers
# =============================================================================


def _headers() -> dict[str, str]:
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("Error: NOTION_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _request(method: str, path: str, body: dict | None = None) -> dict[str, Any]:
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


def _post(path: str, body: dict) -> dict[str, Any]:
    return _request("POST", path, body)


def _patch(path: str, body: dict) -> dict[str, Any]:
    return _request("PATCH", path, body)


def _get(path: str) -> dict[str, Any]:
    return _request("GET", path)


# =============================================================================
# Property helpers
# =============================================================================


def _read_title(props: dict, key: str = "Name") -> str:
    """Extract plain text from a title property."""
    title = props.get(key, {}).get("title", [])
    return title[0]["plain_text"] if title else ""


def _read_status(props: dict) -> str:
    """Read status from either status or select type."""
    raw = props.get("Status", {})
    prop_type = raw.get("type", "")
    val = raw.get(prop_type, {})
    return val.get("name", "") if val else ""


def _read_select(props: dict, key: str) -> str:
    sel = props.get(key, {}).get("select", {})
    return sel.get("name", "") if sel else ""


def _read_people(props: dict, key: str = "Assignee") -> str:
    people = props.get(key, {}).get("people", [])
    return people[0].get("name", "") if people else ""


def _read_unique_id(props: dict) -> str:
    """Extract human-readable ticket ID (e.g. 'GB-123')."""
    for prop in props.values():
        if prop.get("type") == "unique_id":
            uid = prop.get("unique_id", {})
            prefix = uid.get("prefix", "")
            number = uid.get("number")
            if prefix and number is not None:
                return f"{prefix}-{number}"
    return ""


def _read_url(props: dict, key: str) -> str:
    return props.get(key, {}).get("url", "") or ""


def _read_number(props: dict, key: str) -> float | int | None:
    return props.get(key, {}).get("number")


def _read_timestamp(props: dict, key: str) -> str:
    """Read created_time or last_edited_time property."""
    raw = props.get(key, {})
    prop_type = raw.get("type", "")
    return raw.get(prop_type, "") or ""


def _read_formula_date(props: dict, key: str) -> str:
    """Read a formula property that returns a date."""
    raw = props.get(key, {}).get("formula", {})
    if raw.get("type") == "date" and raw.get("date"):
        return raw["date"].get("start", "") or ""
    return ""


_EPOCH_PREFIX = "1970-01-01"


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


def _read_ticket(page: dict) -> dict:
    """Extract common ticket fields from a Notion page."""
    props = page.get("properties", {})
    return {
        "ticket_id": _read_unique_id(props),
        "name": _read_title(props),
        "status": _read_status(props),
        "priority": _read_select(props, "Priority"),
        "assignee": _read_people(props),
        "ah": _read_number(props, "AH"),
        "sort_date": _read_formula_date(props, "Sort Date"),
        "created": _read_timestamp(props, "Created time"),
        "edited": _read_timestamp(props, "Last edited time"),
        "gitlab_mr": _read_url(props, "Gitlab MR"),
        "url": page.get("url", ""),
        "page_id": page.get("id", ""),
    }


def _build_filter_body(config: dict, args: argparse.Namespace, proj: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build filter and sort body for ticket queries.

    Uses project-level ``date_property`` (default: ``Sort Date``) for
    ``--since`` filtering and sort ordering.  The property type defaults to
    ``formula`` but can be overridden per project via ``date_property_type``
    (e.g. ``created_time``).
    """
    date_prop = (proj or {}).get("date_property", "Sort Date")
    date_type = (proj or {}).get("date_property_type", "formula")

    filters: list[dict[str, Any]] = []
    if getattr(args, "assignee", None):
        user_id = resolve_user_id(config, args.assignee)
        if not user_id:
            available = ", ".join(sorted(config.get("users", {}).keys()))
            print(f"Error: unknown assignee '{args.assignee}'. Available: {available}", file=sys.stderr)
            sys.exit(1)
        filters.append({"property": "Assignee", "people": {"contains": user_id}})
    if getattr(args, "status", None):
        filters.append({"property": "Status", "status": {"equals": args.status}})
    if getattr(args, "query", None):
        filters.append({"property": "Name", "title": {"contains": args.query}})
    if getattr(args, "since", None):
        if date_type == "formula":
            filters.append({"property": date_prop, "formula": {"date": {"on_or_after": args.since}}})
        elif date_type == "created_time":
            filters.append({"timestamp": "created_time", "created_time": {"on_or_after": args.since}})
        elif date_type == "last_edited_time":
            filters.append({"timestamp": "last_edited_time", "last_edited_time": {"on_or_after": args.since}})
        else:
            filters.append({"property": date_prop, "date": {"on_or_after": args.since}})

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


def _build_ticket_query(config: dict, args: argparse.Namespace) -> tuple[str, dict]:
    """Build a ticket query for a single project.

    Returns (database_id, query_body).
    """
    proj = get_project_config(config, args.project)
    database_id = proj["database_id"]
    body = _build_filter_body(config, args, proj)
    return database_id, body


def _build_ticket_queries(config: dict, args: argparse.Namespace) -> list[tuple[str, str, dict]]:
    """Build ticket queries across projects.

    When --project is specified, queries that project only.
    When omitted, queries ALL configured projects.

    Returns list of (project_name, database_id, query_body).
    """
    projects = config.get("projects", {})
    if args.project:
        proj = get_project_config(config, args.project)
        body = _build_filter_body(config, args, proj)
        return [(args.project, proj["database_id"], body)]

    result = []
    for name, proj in projects.items():
        body = _build_filter_body(config, args, proj)
        result.append((name, proj["database_id"], body))
    return result


def _markdown_to_blocks(text: str) -> list[dict[str, Any]]:
    """Convert markdown text to Notion blocks.

    Supports headings (h1-h3), to-do items, bulleted lists, and paragraphs.
    Consecutive plain-text lines are joined into a single paragraph block.
    """
    if not text:
        return []

    def _rich_text(content: str) -> list[dict[str, Any]]:
        return [{"type": "text", "text": {"content": content}}]

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
        heading_match = re.match(r'^(#{1,3})\s+(.*)', stripped)
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
        todo_checked = re.match(r'^- \[x\]\s+(.*)', stripped, re.IGNORECASE)
        if todo_checked:
            _flush_paragraph()
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {"rich_text": _rich_text(todo_checked.group(1).strip()), "checked": True},
            })
            continue

        # To-do items (unchecked)
        todo_unchecked = re.match(r'^- \[ \]\s+(.*)', stripped)
        if todo_unchecked:
            _flush_paragraph()
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {"rich_text": _rich_text(todo_unchecked.group(1).strip()), "checked": False},
            })
            continue

        # Bulleted list items
        bullet_match = re.match(r'^- (.*)', stripped)
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
        _request("DELETE", f"/blocks/{bid}")

    # Append new blocks in batches of 100
    if new_blocks:
        for i in range(0, len(new_blocks), 100):
            batch = new_blocks[i:i + 100]
            _patch(f"/blocks/{page_id}/children", {"children": batch})


# =============================================================================
# Query helper (handles pagination)
# =============================================================================


def _query_database(database_id: str, body: dict | None = None) -> list[dict[str, Any]]:
    """Query a Notion database, handling pagination."""
    payload = body or {}
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


# =============================================================================
# Subcommands
# =============================================================================


def cmd_create(args: argparse.Namespace) -> None:
    """Create a ticket."""
    config = load_config(args.config)
    proj = get_project_config(config, args.project)
    database_id = proj["database_id"]

    properties: dict[str, Any] = {
        "Name": {"title": [{"text": {"content": args.title}}]},
    }

    if args.priority:
        properties["Priority"] = {"select": {"name": args.priority}}

    if args.status:
        properties["Status"] = {"status": {"name": args.status}}

    if args.assignee:
        user_id = resolve_user_id(config, args.assignee)
        if not user_id:
            available = ", ".join(sorted(config.get("users", {}).keys()))
            print(f"Error: unknown assignee '{args.assignee}'. Available: {available}", file=sys.stderr)
            sys.exit(1)
        properties["Assignee"] = {"people": [{"id": user_id}]}

    if args.epic:
        # Search epics to find ID by name
        epics_db = proj.get("epics_database_id", "")
        if epics_db:
            epic_id = _find_epic_id(epics_db, args.epic, proj.get("epic_status_type", "select"))
            if epic_id:
                prop_epic = proj.get("prop_epic", "Epic")
                properties[prop_epic] = {"relation": [{"id": epic_id}]}
            else:
                print(f"Warning: epic '{args.epic}' not found, skipping epic link", file=sys.stderr)

    children = _markdown_to_blocks(args.description) if args.description else []

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

    print(f"Created: {args.title}")
    if ticket_id:
        print(f"Ticket: {ticket_id}")
    print(f"ID: {page_id}")
    print(f"URL: {url}")


def _find_epic_id(epics_db: str, epic_name: str, status_type: str) -> str | None:
    """Search epics database for an epic by name, return its page ID."""
    results = _query_database(epics_db, {})
    for page in results:
        props = page.get("properties", {})
        # Epic title can be under "Epic" or "Name"
        name = _read_title(props, "Epic") or _read_title(props, "Name")
        if name.lower() == epic_name.lower():
            return page["id"]
    return None


def cmd_update(args: argparse.Namespace) -> None:
    """Update a ticket."""
    config = load_config(args.config)
    properties: dict[str, Any] = {}

    if args.title:
        properties["Name"] = {"title": [{"text": {"content": args.title}}]}
    if args.status:
        properties["Status"] = {"status": {"name": args.status}}
    if args.priority:
        properties["Priority"] = {"select": {"name": args.priority}}
    if getattr(args, "ah", None) is not None:
        properties["AH"] = {"number": args.ah}
    if args.assignee:
        user_id = resolve_user_id(config, args.assignee)
        if not user_id:
            available = ", ".join(sorted(config.get("users", {}).keys()))
            print(f"Error: unknown assignee '{args.assignee}'. Available: {available}", file=sys.stderr)
            sys.exit(1)
        properties["Assignee"] = {"people": [{"id": user_id}]}

    if not properties and not args.description:
        print("Error: nothing to update. Provide at least one field.", file=sys.stderr)
        sys.exit(1)

    if properties:
        page = _patch(f"/pages/{args.page_id}", {"properties": properties})
    else:
        page = _get(f"/pages/{args.page_id}")

    if args.description:
        _replace_page_blocks(args.page_id, _markdown_to_blocks(args.description))

    url = page.get("url", "")
    print(f"Updated: {args.page_id}")
    print(f"URL: {url}")



def cmd_search(args: argparse.Namespace) -> None:
    """Search tickets."""
    config = load_config(args.config)
    queries = _build_ticket_queries(config, args)

    all_results: list[dict] = []
    for _name, database_id, body in queries:
        all_results.extend(_query_database(database_id, body))

    if not all_results:
        print("No tickets found.")
        return

    total = len(all_results)
    limit = args.limit
    display = all_results if limit == 0 else all_results[:limit]
    truncated = limit > 0 and total > limit

    print(f"Found {total} ticket(s):\n")
    for page in display:
        t = _read_ticket(page)
        ah_str = str(t["ah"]) if t["ah"] is not None else "-"
        label = f"[{t['ticket_id']}]" if t["ticket_id"] else f"[{t['page_id'][:8]}]"
        print(f"  {label} {t['name']}")
        print(f"    Status: {t['status']} | Priority: {t['priority']} | Assignee: {t['assignee']} | AH: {ah_str}")
        print(f"    Sort: {_format_date(t['sort_date'])} | Created: {_format_dt(t['created'])} ({_format_relative(t['created'])}) | Updated: {_format_dt(t['edited'])} ({_format_relative(t['edited'])})")
        if t["gitlab_mr"]:
            print(f"    MR: {t['gitlab_mr']}")
        print(f"    URL: {t['url']}")
        print()

    if truncated:
        print(f"Showing {limit} of {total} ticket(s). Use --limit to see more.")


def cmd_stale(args: argparse.Namespace) -> None:
    """List stale tickets (no status or no AH)."""
    config = load_config(args.config)
    queries = _build_ticket_queries(config, args)

    results: list[dict] = []
    for _name, database_id, body in queries:
        results.extend(_query_database(database_id, body))

    stale: list[tuple[dict, str]] = []
    for page in results:
        t = _read_ticket(page)
        reasons = []
        if not t["status"]:
            reasons.append("no status")
        if t["ah"] is None:
            reasons.append("no AH")
        if reasons:
            stale.append((t, ", ".join(reasons)))

    if not stale:
        print("No stale tickets found.")
        return

    print(f"Found {len(stale)} stale ticket(s):\n")
    for t, reason in stale:
        ah_str = str(t["ah"]) if t["ah"] is not None else "-"
        label = f"[{t['ticket_id']}]" if t["ticket_id"] else f"[{t['page_id'][:8]}]"
        print(f"  {label} {t['name']}  [{reason}]")
        print(f"    Status: {t['status']} | Priority: {t['priority']} | Assignee: {t['assignee']} | AH: {ah_str}")
        print(f"    Sort: {_format_date(t['sort_date'])} | Created: {_format_dt(t['created'])} ({_format_relative(t['created'])}) | Updated: {_format_dt(t['edited'])} ({_format_relative(t['edited'])})")
        if t["gitlab_mr"]:
            print(f"    MR: {t['gitlab_mr']}")
        print(f"    URL: {t['url']}")
        print()


def cmd_epics(args: argparse.Namespace) -> None:
    """List epics."""
    config = load_config(args.config)
    projects = config.get("projects", {})

    if args.project:
        proj_items = [(args.project, get_project_config(config, args.project))]
    else:
        proj_items = list(projects.items())

    all_results: list[dict] = []
    for name, proj in proj_items:
        epics_db = proj.get("epics_database_id", "")
        if not epics_db:
            continue

        status_type = proj.get("epic_status_type", "select")

        body: dict[str, Any] = {"page_size": 100}
        if args.status:
            body["filter"] = {
                "property": "Status",
                status_type: {"equals": args.status},
            }

        all_results.extend(_query_database(epics_db, body))

    if not all_results:
        print("No epics found.")
        return

    results = all_results
    print(f"Found {len(results)} epic(s):\n")
    for page in results:
        props = page.get("properties", {})
        name = _read_title(props, "Epic") or _read_title(props, "Name")
        status = _read_status(props)
        phase = _read_select(props, "Phase")
        url = page.get("url", "")
        page_id = page["id"]

        print(f"  {name}")
        print(f"    Status: {status} | Phase: {phase}")
        print(f"    ID: {page_id}")
        print(f"    URL: {url}")
        print()


def _resolve_ticket_date(t: dict) -> str:
    """Get the best date for a ticket: Sort Date, fallback to Created time."""
    sd = t["sort_date"]
    if sd and not sd.startswith(_EPOCH_PREFIX):
        return sd
    ct = t["created"]
    if ct and not ct.startswith(_EPOCH_PREFIX):
        return ct
    return ""


def cmd_report(args: argparse.Namespace) -> None:
    """AH report grouped by week or month."""
    config = load_config(args.config)
    queries = _build_ticket_queries(config, args)

    results: list[dict] = []
    proj_names: list[str] = []
    for name, database_id, body in queries:
        results.extend(_query_database(database_id, body))
        proj_names.append(name)

    proj_name = ", ".join(proj_names)

    period = getattr(args, "period", "weekly")
    buckets: dict[str, list[float]] = {}

    for page in results:
        t = _read_ticket(page)
        if t["ah"] is None or t["ah"] <= 0:
            continue
        date_str = _resolve_ticket_date(t)
        if not date_str:
            continue
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        if period == "monthly":
            key = dt.strftime("%Y-%m")
        else:
            iso = dt.isocalendar()
            key = f"{iso[0]}-W{iso[1]:02d}"

        buckets.setdefault(key, []).append(float(t["ah"]))

    if not buckets:
        print("No tickets with AH found.")
        return

    sorted_keys = sorted(buckets.keys(), reverse=True)
    total_tickets = 0
    total_ah = 0.0

    print(f"AH Report ({period}) — {proj_name}\n")
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


def cmd_get_ticket(args: argparse.Namespace) -> None:
    """Get full detail for a single ticket by ID or page-id."""
    config = load_config(args.config)
    projects = config.get("projects", {})

    ticket_arg = args.ticket
    match = re.match(r'^([A-Za-z]+)-(\d+)$', ticket_arg)

    if match:
        # Human-readable ticket ID like GB-319
        number = int(match.group(2))
        body = {
            "filter": {
                "property": "ID",
                "unique_id": {"equals": number},
            },
        }

        # Determine which projects to search
        if args.project:
            search_projects = [get_project_config(config, args.project)]
        else:
            search_projects = list(projects.values())

        page = None
        for proj in search_projects:
            results = _query_database(proj["database_id"], body)
            if results:
                # Verify prefix matches the ticket ID
                found_ticket = _read_ticket(results[0])
                if found_ticket["ticket_id"] and found_ticket["ticket_id"].upper() == ticket_arg.upper():
                    page = results[0]
                    break
        if not page:
            print(f"No ticket found matching '{ticket_arg}'.", file=sys.stderr)
            sys.exit(1)
    else:
        # Treat as page-id
        page = _get(f"/pages/{ticket_arg}")

    t = _read_ticket(page)

    ticket_label = t["ticket_id"] or t["page_id"][:8]
    type_str = _read_select(page.get("properties", {}), "Type")
    type_part = f" [{type_str}]" if type_str else ""
    ah_str = str(t["ah"]) if t["ah"] is not None else "-"

    print(f"[{ticket_label}]{type_part} {t['name']}")
    print(f"  Status: {t['status']} | Priority: {t['priority']} | Assignee: {t['assignee']} | AH: {ah_str}")
    print(f"  Sort: {_format_date(t['sort_date'])} | Created: {_format_dt(t['created'])} ({_format_relative(t['created'])}) | Updated: {_format_dt(t['edited'])} ({_format_relative(t['edited'])})")
    if t["gitlab_mr"]:
        print(f"  MR: {t['gitlab_mr']}")
    print(f"  URL: {t['url']}")

    # Read page content (children blocks) as description
    content = _read_page_content(t["page_id"])
    if content.strip():
        print()
        print("  Description:")
        for line in content.splitlines():
            print(f"    {line}")


def cmd_users(args: argparse.Namespace) -> None:
    """Discover workspace users."""
    config = load_config(args.config)

    # Paginated user list
    users: dict[str, str] = {}
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
                users[name.lower()] = user_id

        has_more = resp.get("has_more", False)
        start_cursor = resp.get("next_cursor")

    if not users:
        print("No users found.")
        return

    print(f"Found {len(users)} user(s):\n")
    for name, uid in sorted(users.items()):
        # Mark users already in config
        existing = config.get("users", {})
        marker = " (in config)" if name in existing else ""
        print(f"  {name}: {uid}{marker}")

    # Offer to update config
    new_users = {k: v for k, v in users.items() if k not in config.get("users", {})}
    if new_users:
        print(f"\n{len(new_users)} new user(s) not in config.")
        print("Add --save to update config file (not yet implemented).")


# =============================================================================
# CLI
# =============================================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Notion ticket and epic CLI",
        prog="notion_cli.py",
    )
    parser.add_argument("--config", help="Path to notion.yaml config file")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- create ---
    p_create = subparsers.add_parser("create", help="Create a ticket")
    p_create.add_argument("--title", required=True, help="Ticket title")
    p_create.add_argument("--description", default="", help="Ticket description (markdown)")
    p_create.add_argument(
        "--priority",
        default="Medium",
        choices=["Low", "Medium", "High", "Critical"],
        help="Ticket priority (default: Medium)",
    )
    p_create.add_argument(
        "--status",
        default=None,
        choices=["Not started", "In progress", "Done", "Backlog"],
        help="Ticket status",
    )
    p_create.add_argument("--assignee", help="Assignee name (from config users)")
    p_create.add_argument("--epic", help="Epic name to link (searches epics database)")
    p_create.add_argument("--project", help="Project key (default: from config)")

    # --- update ---
    p_update = subparsers.add_parser("update", help="Update a ticket")
    p_update.add_argument("--page-id", required=True, help="Notion page ID")
    p_update.add_argument("--title", help="New title")
    p_update.add_argument(
        "--status",
        choices=["Not started", "In progress", "Done", "Backlog"],
        help="New status",
    )
    p_update.add_argument(
        "--priority",
        choices=["Low", "Medium", "High", "Critical"],
        help="New priority",
    )
    p_update.add_argument("--assignee", help="New assignee name")
    p_update.add_argument("--ah", type=float, help="Actual working hours")
    p_update.add_argument("--description", help="New description (replaces existing)")

    # --- search ---
    p_search = subparsers.add_parser("search", help="Search tickets")
    p_search.add_argument("--assignee", help="Filter by assignee name")
    p_search.add_argument("--status", help="Filter by status")
    p_search.add_argument("--query", help="Search by title (case-insensitive substring)")
    p_search.add_argument("--since", help="Filter by Sort Date >= YYYY-MM-DD")
    p_search.add_argument("--limit", type=int, default=50, help="Max results to display (default: 50, 0 for all)")
    p_search.add_argument("--project", help="Project key")

    # --- stale ---
    p_stale = subparsers.add_parser("stale", help="List stale tickets (no status or no AH)")
    p_stale.add_argument("--assignee", help="Filter by assignee name")
    p_stale.add_argument("--project", help="Project key")

    # --- epics ---
    p_epics = subparsers.add_parser("epics", help="List epics")
    p_epics.add_argument("--status", help="Filter by status")
    p_epics.add_argument("--project", help="Project key")

    # --- report ---
    p_report = subparsers.add_parser("report", help="AH report by week or month")
    p_report.add_argument(
        "--period",
        default="weekly",
        choices=["weekly", "monthly"],
        help="Group by week or month (default: weekly)",
    )
    p_report.add_argument("--assignee", help="Filter by assignee name")
    p_report.add_argument("--project", help="Project key")

    # --- get-ticket ---
    p_get_ticket = subparsers.add_parser("get-ticket", help="Get full detail for a single ticket")
    p_get_ticket.add_argument("ticket", help="Ticket ID (e.g. GB-319) or Notion page-id")
    p_get_ticket.add_argument("--project", help="Project key")

    # --- users ---
    subparsers.add_parser("users", help="Discover workspace users")

    args = parser.parse_args()

    commands = {
        "create": cmd_create,
        "update": cmd_update,
        "search": cmd_search,
        "stale": cmd_stale,
        "epics": cmd_epics,
        "report": cmd_report,
        "get-ticket": cmd_get_ticket,
        "users": cmd_users,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
