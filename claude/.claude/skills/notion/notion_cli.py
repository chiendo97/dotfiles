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


def _read_rich_text(props: dict, key: str) -> str:
    """Extract plain text from a rich_text property."""
    texts = props.get(key, {}).get("rich_text", [])
    return "".join(t.get("plain_text", "") for t in texts)


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
        "description": _read_rich_text(props, "Description"),
        "url": page.get("url", ""),
        "page_id": page.get("id", ""),
    }


def _build_ticket_query(config: dict, args: argparse.Namespace) -> tuple[str, dict]:
    """Build a ticket query with optional assignee filter and Sort Date ordering.

    Returns (database_id, query_body).
    """
    proj = get_project_config(config, args.project)
    database_id = proj["database_id"]

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

    body: dict[str, Any] = {
        "page_size": 100,
        "sorts": [{"property": "Sort Date", "direction": "descending"}],
    }
    if len(filters) == 1:
        body["filter"] = filters[0]
    elif len(filters) > 1:
        body["filter"] = {"and": filters}

    return database_id, body



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

    if args.description:
        properties["Description"] = {
            "rich_text": [{"type": "text", "text": {"content": args.description}}]
        }

    payload: dict[str, Any] = {
        "parent": {"database_id": database_id},
        "properties": properties,
    }

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

    if args.description:
        properties["Description"] = {
            "rich_text": [{"type": "text", "text": {"content": args.description}}]
        }

    if not properties:
        print("Error: nothing to update. Provide at least one field.", file=sys.stderr)
        sys.exit(1)

    page = _patch(f"/pages/{args.page_id}", {"properties": properties})

    url = page.get("url", "")
    print(f"Updated: {args.page_id}")
    print(f"URL: {url}")



def cmd_search(args: argparse.Namespace) -> None:
    """Search tickets."""
    config = load_config(args.config)
    database_id, body = _build_ticket_query(config, args)
    results = _query_database(database_id, body)

    if not results:
        print("No tickets found.")
        return

    print(f"Found {len(results)} ticket(s):\n")
    for page in results:
        t = _read_ticket(page)
        ah_str = str(t["ah"]) if t["ah"] is not None else "-"
        label = f"[{t['ticket_id']}]" if t["ticket_id"] else f"[{t['page_id'][:8]}]"
        print(f"  {label} {t['name']}")
        print(f"    Status: {t['status']} | Priority: {t['priority']} | Assignee: {t['assignee']} | AH: {ah_str}")
        print(f"    Sort: {_format_date(t['sort_date'])} | Created: {_format_dt(t['created'])} ({_format_relative(t['created'])}) | Updated: {_format_dt(t['edited'])} ({_format_relative(t['edited'])})")
        print(f"    URL: {t['url']}")
        print()


def cmd_stale(args: argparse.Namespace) -> None:
    """List stale tickets (no status or no AH)."""
    config = load_config(args.config)
    database_id, body = _build_ticket_query(config, args)
    results = _query_database(database_id, body)

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
        print(f"    URL: {t['url']}")
        print()


def cmd_epics(args: argparse.Namespace) -> None:
    """List epics."""
    config = load_config(args.config)
    proj = get_project_config(config, args.project)
    epics_db = proj.get("epics_database_id", "")
    if not epics_db:
        print("Error: no epics_database_id configured for this project", file=sys.stderr)
        sys.exit(1)

    status_type = proj.get("epic_status_type", "select")

    body: dict[str, Any] = {"page_size": 100}
    if args.status:
        body["filter"] = {
            "property": "Status",
            status_type: {"equals": args.status},
        }

    results = _query_database(epics_db, body)

    if not results:
        print("No epics found.")
        return

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
    database_id, body = _build_ticket_query(config, args)
    results = _query_database(database_id, body)

    proj = get_project_config(config, args.project)
    proj_name = args.project or config.get("default_project", "")

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
        "users": cmd_users,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
