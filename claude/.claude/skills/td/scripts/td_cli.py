#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_API_BASE = "https://api.todoist.com/api/v1"


class TodoistError(RuntimeError):
    pass


class TodoistClient:
    def __init__(self, token: str, api_base: str = DEFAULT_API_BASE) -> None:
        self.token = token
        self.api_base = api_base.rstrip("/")

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str | int] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.api_base}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        body = None
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }
        if payload is not None:
            body = json.dumps(payload).encode()
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace").strip()
            message = f"Todoist API HTTP {exc.code}"
            if detail:
                message = f"{message}: {detail}"
            raise TodoistError(message) from exc
        except urllib.error.URLError as exc:
            raise TodoistError(f"Todoist API request failed: {exc.reason}") from exc

        if not raw:
            return None
        return json.loads(raw)

    def get_projects(self) -> list[dict[str, Any]]:
        return collect_pages(self, "/projects/search", {"query": "*", "limit": 200})

    def get_sections(self, project_id: str | None = None) -> list[dict[str, Any]]:
        params: dict[str, str | int] = {"limit": 200}
        if project_id:
            params["project_id"] = project_id
        return collect_pages(self, "/sections", params)

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.request("POST", "/tasks", payload=payload)
        if not isinstance(result, dict):
            raise TodoistError("Todoist returned an unexpected task response")
        return result


def collect_pages(
    client: TodoistClient,
    path: str,
    params: dict[str, str | int],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        page_params = dict(params)
        if cursor:
            page_params["cursor"] = cursor
        page = client.request("GET", path, params=page_params)
        if isinstance(page, list):
            results.extend(page)
            return results
        if not isinstance(page, dict):
            raise TodoistError(f"Todoist returned an unexpected response for {path}")
        page_results = page.get("results", [])
        if not isinstance(page_results, list):
            raise TodoistError(f"Todoist returned malformed results for {path}")
        results.extend(page_results)
        cursor = page.get("next_cursor")
        if not cursor:
            return results


def normalized(value: str) -> str:
    return " ".join(value.strip().split()).casefold()


def item_id(item: dict[str, Any]) -> str:
    value = item.get("id")
    if not isinstance(value, str) or not value:
        raise TodoistError(f"Todoist item is missing an id: {item!r}")
    return value


def item_name(item: dict[str, Any]) -> str:
    value = item.get("name")
    if not isinstance(value, str) or not value:
        raise TodoistError(f"Todoist item is missing a name: {item!r}")
    return value


def resolve_named_item(
    items: list[dict[str, Any]],
    query: str,
    kind: str,
    *,
    describe_item,
) -> dict[str, Any]:
    query_norm = normalized(query)
    matches = [
        item
        for item in items
        if normalized(item_id(item)) == query_norm or normalized(item_name(item)) == query_norm
    ]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        available = ", ".join(sorted(describe_item(item) for item in items))
        raise TodoistError(f"No {kind} matched {query!r}. Available: {available}")

    options = ", ".join(sorted(describe_item(item) for item in matches))
    raise TodoistError(f"Ambiguous {kind} {query!r}. Use an exact ID or project scope. Matches: {options}")


def project_label(project: dict[str, Any]) -> str:
    return item_name(project)


def section_label(
    section: dict[str, Any],
    project_by_id: dict[str, str],
) -> str:
    project_name = project_by_id.get(str(section.get("project_id")), str(section.get("project_id")))
    return f"{project_name} / {item_name(section)}"


def resolve_project(client, project: str | None) -> tuple[str | None, dict[str, str]]:
    projects = client.get_projects()
    project_by_id = {item_id(item): item_name(item) for item in projects}
    if project is None:
        return None, project_by_id
    match = resolve_named_item(
        projects,
        project,
        "project",
        describe_item=project_label,
    )
    return item_id(match), project_by_id


def resolve_section(
    client,
    section: str | None,
    *,
    project_id: str | None,
    project_by_id: dict[str, str],
) -> str | None:
    if section is None:
        return None
    sections = client.get_sections(project_id=project_id)
    match = resolve_named_item(
        sections,
        section,
        "section",
        describe_item=lambda item: section_label(item, project_by_id),
    )
    return item_id(match)


def build_payload(
    *,
    header: str,
    details: str,
    project_id: str | None,
    section_id: str | None,
    labels: list[str],
    due: str | None,
    priority: int | None,
) -> dict[str, Any]:
    if not header.strip():
        raise TodoistError("Task header cannot be empty")

    payload: dict[str, Any] = {"content": header.strip()}
    if details.strip():
        payload["description"] = details.strip()
    if project_id:
        payload["project_id"] = project_id
    if section_id:
        payload["section_id"] = section_id
    if labels:
        payload["labels"] = labels
    if due:
        payload["due_string"] = due
    if priority is not None:
        if priority < 1 or priority > 4:
            raise TodoistError("Priority must be between 1 and 4")
        payload["priority"] = priority
    return payload


def create_task_from_args(
    *,
    client,
    header: str,
    details: str,
    project: str | None,
    section: str | None,
    labels: list[str],
    due: str | None,
    priority: int | None,
    dry_run: bool,
) -> dict[str, Any]:
    project_id, project_by_id = resolve_project(client, project)
    section_id = resolve_section(
        client,
        section,
        project_id=project_id,
        project_by_id=project_by_id,
    )
    payload = build_payload(
        header=header,
        details=details,
        project_id=project_id,
        section_id=section_id,
        labels=labels,
        due=due,
        priority=priority,
    )
    if dry_run:
        return {"dry_run": True, "payload": payload}
    return client.create_task(payload)


def read_details(details: str | None, details_file: str | None) -> str:
    parts: list[str] = []
    if details:
        parts.append(details)
    if details_file:
        if details_file == "-":
            parts.append(sys.stdin.read())
        else:
            parts.append(Path(details_file).read_text())
    return "\n\n".join(part.strip() for part in parts if part.strip())


def env_token() -> str:
    token = os.environ.get("TODOIST_API_TOKEN") or os.environ.get("TODOIST_API_KEY")
    if not token:
        raise TodoistError("Set TODOIST_API_TOKEN or TODOIST_API_KEY before using td_cli.py")
    return token


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def list_projects(client: TodoistClient) -> None:
    for project in client.get_projects():
        print(f"{item_id(project)}\t{item_name(project)}")


def list_sections(client: TodoistClient, project: str | None) -> None:
    project_id, project_by_id = resolve_project(client, project)
    for section in client.get_sections(project_id=project_id):
        print(f"{item_id(section)}\t{section_label(section, project_by_id)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Todoist task helper for agent skills.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add = subparsers.add_parser("add", help="Create a Todoist task")
    add.add_argument("--project", help="Project name or ID")
    add.add_argument("--section", help="Section name or ID, scoped by --project when provided")
    add.add_argument("--header", required=True, help="Short task title")
    add.add_argument("--details", help="Task description text")
    add.add_argument("--details-file", help="Read description text from a file, or '-' for stdin")
    add.add_argument("--label", action="append", default=[], help="Label to add; repeat as needed")
    add.add_argument("--due", help='Natural language due date, e.g. "tomorrow"')
    add.add_argument("--priority", type=int, choices=range(1, 5), help="Todoist priority 1-4")
    add.add_argument("--dry-run", action="store_true", help="Print payload without creating a task")

    subparsers.add_parser("list-projects", help="List Todoist projects")
    sections = subparsers.add_parser("list-sections", help="List Todoist sections")
    sections.add_argument("--project", help="Only list sections in this project")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    client = TodoistClient(
        env_token(),
        api_base=os.environ.get("TODOIST_API_BASE", DEFAULT_API_BASE),
    )

    try:
        if args.command == "list-projects":
            list_projects(client)
        elif args.command == "list-sections":
            list_sections(client, args.project)
        elif args.command == "add":
            task = create_task_from_args(
                client=client,
                header=args.header,
                details=read_details(args.details, args.details_file),
                project=args.project,
                section=args.section,
                labels=args.label,
                due=args.due,
                priority=args.priority,
                dry_run=args.dry_run,
            )
            if args.dry_run:
                print_json(task["payload"])
            else:
                url = task.get("url", "")
                print(f"Created Todoist task: {task.get('content', args.header)}")
                if url:
                    print(url)
        else:
            parser.error(f"unknown command: {args.command}")
    except TodoistError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
