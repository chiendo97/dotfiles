from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).with_name("scripts") / "td_cli.py"
spec = importlib.util.spec_from_file_location("td_cli", SCRIPT)
assert spec is not None
td_cli = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(td_cli)


class FakeClient:
    def __init__(self) -> None:
        self.projects = [
            {"id": "p-inbox", "name": "Inbox"},
            {"id": "p-area", "name": "Area"},
            {"id": "p-project", "name": "Project"},
        ]
        self.sections = [
            {"id": "s-home", "name": "Home", "project_id": "p-area"},
            {"id": "s-codex", "name": "Codex", "project_id": "p-project"},
            {"id": "s-family-area", "name": "Family", "project_id": "p-area"},
            {"id": "s-family-project", "name": "Family", "project_id": "p-project"},
        ]
        self.created_payload = None

    def get_projects(self):
        return self.projects

    def get_sections(self, project_id=None):
        if project_id is None:
            return self.sections
        return [s for s in self.sections if s["project_id"] == project_id]

    def create_task(self, payload):
        self.created_payload = payload
        return {
            "id": "task-1",
            "content": payload["content"],
            "description": payload.get("description", ""),
            "project_id": payload.get("project_id"),
            "section_id": payload.get("section_id"),
            "url": "https://todoist.com/showTask?id=task-1",
        }


def test_create_task_resolves_project_and_section_names() -> None:
    client = FakeClient()

    task = td_cli.create_task_from_args(
        client=client,
        header="Fix backup warning",
        details="Investigate the failed snapshot and record the result.",
        project="Area",
        section="Home",
        labels=[],
        due=None,
        priority=None,
        dry_run=False,
    )

    assert client.created_payload == {
        "content": "Fix backup warning",
        "description": "Investigate the failed snapshot and record the result.",
        "project_id": "p-area",
        "section_id": "s-home",
    }
    assert task["url"].endswith("task-1")


def test_section_resolution_is_scoped_to_project() -> None:
    client = FakeClient()

    task = td_cli.create_task_from_args(
        client=client,
        header="Call family",
        details="Full details",
        project="Area",
        section="Family",
        labels=[],
        due=None,
        priority=None,
        dry_run=False,
    )

    assert task["section_id"] == "s-family-area"


def test_ambiguous_section_without_project_raises_clear_error() -> None:
    client = FakeClient()

    try:
        td_cli.create_task_from_args(
            client=client,
            header="Call family",
            details="Full details",
            project=None,
            section="Family",
            labels=[],
            due=None,
            priority=None,
            dry_run=False,
        )
    except td_cli.TodoistError as exc:
        assert "Ambiguous section" in str(exc)
        assert "Project / Family" in str(exc)
        assert "Area / Family" in str(exc)
    else:
        raise AssertionError("expected ambiguous section error")


def test_dry_run_does_not_create_task() -> None:
    client = FakeClient()

    task = td_cli.create_task_from_args(
        client=client,
        header="Write runbook",
        details="Capture steps and rollback.",
        project="Project",
        section="Codex",
        labels=["docs", "codex"],
        due="tomorrow",
        priority=2,
        dry_run=True,
    )

    assert client.created_payload is None
    assert task["dry_run"] is True
    assert task["payload"] == {
        "content": "Write runbook",
        "description": "Capture steps and rollback.",
        "project_id": "p-project",
        "section_id": "s-codex",
        "labels": ["docs", "codex"],
        "due_string": "tomorrow",
        "priority": 2,
    }
