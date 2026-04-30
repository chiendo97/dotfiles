# GitLab Issue & Milestone Management — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend `gitlab_cli.py` with full issue CRUD and cross-repo milestone reporting.

**Architecture:** Add config loading (YAML), new Pydantic models (Issue, Milestone, MilestoneReport), a cross-repo helper (`_for_each_project`), and 10 new typer commands to the existing CLI. Config is optional — existing MR commands stay untouched.

**Tech Stack:** Python 3.10+, typer, pydantic, pyyaml, certifi, urllib (stdlib)

**Spec:** [`docs/superpowers/specs/2026-04-05-gitlab-issue-milestone-skill-design.md`](../specs/2026-04-05-gitlab-issue-milestone-skill-design.md)

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `.claude/skills/gitlab/gitlab_cli.py` | Modify | Add config, models, cross-repo helper, 10 commands |
| `.claude/skills/gitlab/SKILL.md` | Modify | Add issue/milestone docs, config setup, triggers |
| `.claude/rules/skill-invocation.md` | Modify | Add natural language triggers for issue/milestone |
| `config/gitlab.yaml.example` | Create | Example config for users to copy |

---

## Task 1: Add pyyaml dependency and config models

**Files:**
- Modify: `.claude/skills/gitlab/gitlab_cli.py:1-5` (PEP 723 header)
- Modify: `.claude/skills/gitlab/gitlab_cli.py:43-48` (module state)

- [ ] **Step 1: Add `pyyaml` to PEP 723 dependencies**

In `.claude/skills/gitlab/gitlab_cli.py`, change line 4:

```python
# dependencies = ["certifi", "typer", "pydantic"]
```

to:

```python
# dependencies = ["certifi", "typer", "pydantic", "pyyaml"]
```

- [ ] **Step 2: Add yaml import**

After `import urllib.request` (line 28), add:

```python
from pathlib import Path

import yaml
```

And add `pyyaml` type stub note — no changes needed since yaml is untyped, just `import yaml` works.

- [ ] **Step 3: Add config Pydantic models**

After the `SSL_CTX = ...` line (line 34), before the `app = typer.Typer(...)` block, add:

```python
# ---------------------------------------------------------------------------
# Config Models
# ---------------------------------------------------------------------------


class ProjectConfig(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    project_id: str


class GitLabConfig(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    default_instance: str = "git.urieljsc.com"
    projects: dict[str, ProjectConfig] = {}
```

- [ ] **Step 4: Add `_config` to module state**

After `_project_id: str = ""` (line 48), add:

```python
_config: GitLabConfig | None = None
```

- [ ] **Step 5: Add config loading helper**

After the `_detect_project_path()` function (after line 227), add:

```python
def _load_config(config_path: str | None = None) -> GitLabConfig | None:
    """Load gitlab.yaml from explicit path or fallback locations."""
    candidates: list[Path] = []
    if config_path:
        candidates.append(Path(config_path))
    else:
        candidates.append(Path("config/gitlab.yaml"))
        candidates.append(Path.home() / "Source/claude-boy/config/gitlab.yaml")

    for path in candidates:
        if path.is_file():
            with open(path) as f:
                data = yaml.safe_load(f)
            if data:
                return GitLabConfig.model_validate(data)
    return None
```

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/gitlab/gitlab_cli.py
git commit -m "[feat] Add config models and yaml loading to gitlab CLI"
```

---

## Task 2: Extend callback with `--config-path` and named project resolution

**Files:**
- Modify: `.claude/skills/gitlab/gitlab_cli.py` (callback function)

- [ ] **Step 1: Update `main_callback` signature**

Replace the existing `main_callback` function with:

```python
@app.callback()
def main_callback(
    project: Annotated[str | None, typer.Option(help="Named project from config, or path (group/repo). Auto-detected from git remote.")] = None,
    host: Annotated[str | None, typer.Option(help="GitLab host. Auto-detected from glab config.")] = None,
    config_path: Annotated[str | None, typer.Option("--config-path", help="Path to gitlab.yaml config")] = None,
) -> None:
    """GitLab CLI — MR discussions, issues, and milestones."""
    global _token, _base_url, _project_id, _config  # noqa: PLW0603

    _token = os.environ.get("GITLAB_TOKEN", "")
    if not _token:
        # Try glab's stored token
        try:
            result = subprocess.run(
                ["glab", "auth", "status", "-t"],
                capture_output=True,
                text=True,
            )
            # glab prints "Token: glpat-..." to stderr
            for line in result.stderr.splitlines():
                if "Token:" in line:
                    _token = line.split("Token:")[-1].strip()
                    break
        except FileNotFoundError:
            pass

    if not _token:
        print("Error: Set GITLAB_TOKEN or authenticate via `glab auth login`.", file=sys.stderr)
        raise typer.Exit(code=1)

    # Load config (optional)
    _config = _load_config(config_path)

    # Resolve project: named config entry > literal path > git remote
    project_path: str | None = None
    if project and _config and project in _config.projects:
        project_path = _config.projects[project].project_id
    elif project:
        project_path = project  # Treat as literal group/repo path
    else:
        project_path = _detect_project_path()

    gitlab_host = host or (
        _config.default_instance if _config else None
    ) or _detect_gitlab_host()
    _base_url = f"https://{gitlab_host}"
    _project_id = urllib.parse.quote(project_path, safe="")
```

- [ ] **Step 2: Verify existing commands still work**

```bash
uv run .claude/skills/gitlab/gitlab_cli.py --help
```

Expected: Help text shows all existing commands plus the new `--config-path` option.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/gitlab/gitlab_cli.py
git commit -m "[feat] Extend gitlab CLI callback with config loading and named projects"
```

---

## Task 3: Add cross-repo helper `_for_each_project`

**Files:**
- Modify: `.claude/skills/gitlab/gitlab_cli.py` (after API helpers section)

- [ ] **Step 1: Add the helper function**

After the `_build_position` function, add:

```python
def _for_each_project(
    path_template: str,
    params: dict[str, str] | None = None,
) -> list[tuple[str, list[dict[str, Any]]]]:
    """Run GET against all configured projects.

    Args:
        path_template: API path with `:id` placeholder (e.g., "projects/:id/issues").
        params: Query parameters to append.

    Returns:
        List of (project_id, json_response) tuples. Projects that fail are
        logged to stderr and skipped.
    """
    if not _config or not _config.projects:
        print("Error: No projects configured. Create config/gitlab.yaml.", file=sys.stderr)
        raise typer.Exit(code=1)

    results: list[tuple[str, list[dict[str, Any]]]] = []
    for name, proj in _config.projects.items():
        encoded = urllib.parse.quote(proj.project_id, safe="")
        resolved = path_template.replace(":id", encoded)
        url = f"{_base_url}/api/v4/{resolved}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        headers = {"PRIVATE-TOKEN": _token}
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, context=SSL_CTX) as resp:
                raw = resp.read().decode()
                data = json.loads(raw) if raw.strip() else []
            results.append((proj.project_id, data))
        except urllib.error.HTTPError as e:
            print(f"warning: {proj.project_id}: {e.code} {e.reason} -- skipped", file=sys.stderr)

    return results
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/gitlab/gitlab_cli.py
git commit -m "[feat] Add cross-repo helper _for_each_project"
```

---

## Task 4: Add Issue and Milestone domain models

**Files:**
- Modify: `.claude/skills/gitlab/gitlab_cli.py` (Pydantic Models section)

- [ ] **Step 1: Add enums after the config models**

After the `GitLabConfig` class, add:

```python
# ---------------------------------------------------------------------------
# Enums (write operations only)
# ---------------------------------------------------------------------------


class IssueState(str, Enum):
    OPENED = "opened"
    CLOSED = "closed"


class MilestoneState(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
```

Also add `from enum import Enum` to the imports at the top (after `import json`).

- [ ] **Step 2: Add Milestone model**

In the Pydantic Models section, after the `MRInfo` class, add:

```python
class Milestone(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    id: int
    iid: int
    title: str
    description: str | None = None
    state: str
    due_date: str | None = None
    web_url: str

    def display(self) -> str:
        parts = [f"#{self.iid} {self.title} ({self.state})"]
        if self.due_date:
            parts.append(f"  Due: {self.due_date}")
        if self.description:
            desc = self.description[:200]
            if len(self.description) > 200:
                desc += "..."
            parts.append(f"  {desc}")
        parts.append(f"  {self.web_url}")
        return "\n".join(parts)
```

- [ ] **Step 3: Add Issue model**

After the `Milestone` class, add:

```python
class Issue(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    id: int
    iid: int
    title: str
    state: str
    labels: list[str] = []
    assignee: Author | None = None
    milestone: Milestone | None = None
    due_date: str | None = None
    web_url: str
    description: str | None = None

    def display_compact(self) -> str:
        """One-liner for list views."""
        status = "closed" if self.state == "closed" else "open"
        parts = [f"  {status:<6}  #{self.iid:<4} {self.title}"]
        if self.assignee:
            parts.append(f"  @{self.assignee.username}")
        if self.labels:
            parts.append(f"  {','.join(self.labels)}")
        return "".join(parts)

    def display(self) -> str:
        """Full detail view."""
        status = "closed" if self.state == "closed" else "open"
        lines = [f"#{self.iid} {self.title} ({status})"]
        if self.assignee:
            lines.append(f"  Assignee: @{self.assignee.username}")
        if self.labels:
            lines.append(f"  Labels: {', '.join(self.labels)}")
        if self.milestone:
            lines.append(f"  Milestone: {self.milestone.title}")
        if self.due_date:
            lines.append(f"  Due: {self.due_date}")
        lines.append(f"  {self.web_url}")
        if self.description:
            desc = self.description[:500]
            if len(self.description) > 500:
                desc += "..."
            lines.append(f"\n{desc}")
        return "\n".join(lines)
```

- [ ] **Step 4: Add MilestoneReport model**

After the `Issue` class, add:

```python
class MilestoneReport(BaseModel):
    """Per-project milestone stats for aggregated report."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    project: str
    milestone: Milestone
    issues: list[Issue] = []

    @property
    def total_count(self) -> int:
        return len(self.issues)

    @property
    def closed_count(self) -> int:
        return sum(1 for i in self.issues if i.state == "closed")

    @property
    def progress_pct(self) -> float:
        if not self.issues:
            return 0.0
        return (self.closed_count / self.total_count) * 100

    def display(self) -> str:
        due = f"Due: {self.milestone.due_date}" if self.milestone.due_date else "No due date"
        header = f"  {self.project}  -- {due} -- {self.closed_count}/{self.total_count} closed ({self.progress_pct:.0f}%)"
        lines = [header]
        for issue in self.issues:
            lines.append(issue.display_compact())
        return "\n".join(lines)
```

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/gitlab/gitlab_cli.py
git commit -m "[feat] Add Issue, Milestone, MilestoneReport models and enums"
```

---

## Task 5: Implement issue commands — `issue-create` and `issue-get`

**Files:**
- Modify: `.claude/skills/gitlab/gitlab_cli.py` (Commands section)

- [ ] **Step 1: Add `issue-create` command**

After the `batch_inline` command (before `if __name__ == "__main__":`), add:

```python
# ---------------------------------------------------------------------------
# Issue Commands
# ---------------------------------------------------------------------------


@app.command()
def issue_create(
    title: Annotated[str, typer.Option(help="Issue title")],
    description: Annotated[str | None, typer.Option(help="Issue description (markdown)")] = None,
    labels: Annotated[str | None, typer.Option(help="Comma-separated labels")] = None,
    milestone: Annotated[str | None, typer.Option(help="Milestone title to assign")] = None,
    assignee: Annotated[str | None, typer.Option(help="Assignee username")] = None,
    due_date: Annotated[str | None, typer.Option(help="Due date (YYYY-MM-DD)")] = None,
) -> None:
    """Create a new issue."""
    data: dict[str, Any] = {"title": title}
    if description:
        data["description"] = description
    if labels:
        data["labels"] = labels
    if due_date:
        data["due_date"] = due_date
    if assignee:
        # Resolve username to user ID
        try:
            users: list[dict[str, Any]] = api_request(f"projects/:id/members/all?query={assignee}")
            if users:
                data["assignee_ids"] = [users[0]["id"]]
        except GitLabAPIError as e:
            print(f"warning: Could not resolve assignee '{assignee}': {e}", file=sys.stderr)
    if milestone:
        # Resolve milestone title to ID
        try:
            milestones: list[dict[str, Any]] = api_request(
                f"projects/:id/milestones?title={urllib.parse.quote(milestone)}"
            )
            if milestones:
                data["milestone_id"] = milestones[0]["id"]
            else:
                print(f"warning: Milestone '{milestone}' not found — creating without it", file=sys.stderr)
        except GitLabAPIError as e:
            print(f"warning: Could not resolve milestone '{milestone}': {e}", file=sys.stderr)

    try:
        resp: dict[str, Any] = api_request("projects/:id/issues", method="POST", data=data)
    except GitLabAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)

    issue = Issue.model_validate(resp)
    print(f"Created issue #{issue.iid}")
    print(issue.display())
```

- [ ] **Step 2: Add `issue-get` command**

```python
@app.command()
def issue_get(
    iid: Annotated[int, typer.Argument(help="Issue IID")],
) -> None:
    """Get issue details."""
    try:
        resp: dict[str, Any] = api_request(f"projects/:id/issues/{iid}")
    except GitLabAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)

    issue = Issue.model_validate(resp)
    print(issue.display())
```

- [ ] **Step 3: Test manually**

```bash
uv run .claude/skills/gitlab/gitlab_cli.py issue-get --project zariel/claude-boy 1
```

Expected: Shows issue #1 details (the deployment issue we created earlier).

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/gitlab/gitlab_cli.py
git commit -m "[feat] Add issue-create and issue-get commands"
```

---

## Task 6: Implement `issue-update`, `issue-close`, `issue-reopen`

**Files:**
- Modify: `.claude/skills/gitlab/gitlab_cli.py` (Issue Commands section)

- [ ] **Step 1: Add `issue-update` command**

After `issue_get`, add:

```python
@app.command()
def issue_update(
    iid: Annotated[int, typer.Argument(help="Issue IID")],
    title: Annotated[str | None, typer.Option(help="New title")] = None,
    description: Annotated[str | None, typer.Option(help="New description")] = None,
    labels: Annotated[str | None, typer.Option(help="Comma-separated labels (replaces all)")] = None,
    milestone: Annotated[str | None, typer.Option(help="Milestone title")] = None,
    assignee: Annotated[str | None, typer.Option(help="Assignee username")] = None,
    due_date: Annotated[str | None, typer.Option(help="Due date (YYYY-MM-DD)")] = None,
    state: Annotated[IssueState | None, typer.Option(help="State: opened or closed")] = None,
) -> None:
    """Update an existing issue."""
    data: dict[str, Any] = {}
    if title:
        data["title"] = title
    if description is not None:
        data["description"] = description
    if labels is not None:
        data["labels"] = labels
    if due_date is not None:
        data["due_date"] = due_date
    if state:
        data["state_event"] = "close" if state == IssueState.CLOSED else "reopen"
    if assignee:
        try:
            users: list[dict[str, Any]] = api_request(f"projects/:id/members/all?query={assignee}")
            if users:
                data["assignee_ids"] = [users[0]["id"]]
        except GitLabAPIError as e:
            print(f"warning: Could not resolve assignee '{assignee}': {e}", file=sys.stderr)
    if milestone:
        try:
            milestones: list[dict[str, Any]] = api_request(
                f"projects/:id/milestones?title={urllib.parse.quote(milestone)}"
            )
            if milestones:
                data["milestone_id"] = milestones[0]["id"]
            else:
                print(f"warning: Milestone '{milestone}' not found", file=sys.stderr)
        except GitLabAPIError as e:
            print(f"warning: Could not resolve milestone '{milestone}': {e}", file=sys.stderr)

    if not data:
        print("Nothing to update — provide at least one option.")
        return

    try:
        resp: dict[str, Any] = api_request(f"projects/:id/issues/{iid}", method="PUT", data=data)
    except GitLabAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)

    issue = Issue.model_validate(resp)
    print(f"Updated issue #{issue.iid}")
    print(issue.display())
```

- [ ] **Step 2: Add `issue-close` command**

```python
@app.command()
def issue_close(
    iid: Annotated[int, typer.Argument(help="Issue IID")],
) -> None:
    """Close an issue."""
    try:
        resp: dict[str, Any] = api_request(
            f"projects/:id/issues/{iid}", method="PUT", data={"state_event": "close"},
        )
    except GitLabAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)

    issue = Issue.model_validate(resp)
    print(f"Closed issue #{issue.iid}: {issue.title}")
```

- [ ] **Step 3: Add `issue-reopen` command**

```python
@app.command()
def issue_reopen(
    iid: Annotated[int, typer.Argument(help="Issue IID")],
) -> None:
    """Reopen an issue."""
    try:
        resp: dict[str, Any] = api_request(
            f"projects/:id/issues/{iid}", method="PUT", data={"state_event": "reopen"},
        )
    except GitLabAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)

    issue = Issue.model_validate(resp)
    print(f"Reopened issue #{issue.iid}: {issue.title}")
```

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/gitlab/gitlab_cli.py
git commit -m "[feat] Add issue-update, issue-close, issue-reopen commands"
```

---

## Task 7: Implement `issue-list` with cross-repo support

**Files:**
- Modify: `.claude/skills/gitlab/gitlab_cli.py` (Issue Commands section)

- [ ] **Step 1: Add `AllProjectsOpt` type alias**

After `MRNumberOpt` (shared option aliases section), add:

```python
AllProjectsOpt = Annotated[bool, typer.Option("--all-projects", help="Query all configured projects")]
```

- [ ] **Step 2: Add `issue-list` command**

After `issue_reopen`, add:

```python
@app.command()
def issue_list(
    all_projects: AllProjectsOpt = False,
    state: Annotated[str | None, typer.Option(help="Filter by state (opened, closed, all)")] = None,
    labels: Annotated[str | None, typer.Option(help="Filter by labels (comma-separated)")] = None,
    milestone: Annotated[str | None, typer.Option(help="Filter by milestone title")] = None,
    assignee: Annotated[str | None, typer.Option(help="Filter by assignee username")] = None,
    search: Annotated[str | None, typer.Option(help="Search in title and description")] = None,
) -> None:
    """List issues, optionally across all configured projects."""
    params: dict[str, str] = {}
    if state:
        params["state"] = state
    if labels:
        params["labels"] = labels
    if milestone:
        params["milestone"] = milestone
    if assignee:
        params["assignee_username"] = assignee
    if search:
        params["search"] = search
    params["per_page"] = "50"

    if all_projects:
        results = _for_each_project("projects/:id/issues", params)
        all_issues: list[tuple[str, Issue]] = []
        for project_id, issues_data in results:
            for item in issues_data:
                all_issues.append((project_id, Issue.model_validate(item)))

        if not all_issues:
            print("No issues found.")
            return

        # Group by project
        current_project = ""
        for project_id, issue in all_issues:
            if project_id != current_project:
                if current_project:
                    print()
                print(f"{project_id}:")
                current_project = project_id
            print(issue.display_compact())
    else:
        query = "?" + urllib.parse.urlencode(params) if params else ""
        try:
            resp: list[dict[str, Any]] = api_request(f"projects/:id/issues{query}")
        except GitLabAPIError as e:
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)

        if not resp:
            print("No issues found.")
            return

        for item in resp:
            issue = Issue.model_validate(item)
            print(issue.display_compact())
```

- [ ] **Step 3: Test manually**

```bash
# Single project
uv run .claude/skills/gitlab/gitlab_cli.py issue-list --project zariel/claude-boy

# Cross-repo (needs config)
uv run .claude/skills/gitlab/gitlab_cli.py issue-list --all-projects --config-path config/gitlab.yaml
```

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/gitlab/gitlab_cli.py
git commit -m "[feat] Add issue-list with cross-repo support"
```

---

## Task 8: Implement milestone commands — `milestone-create`, `milestone-update`, `milestone-list`

**Files:**
- Modify: `.claude/skills/gitlab/gitlab_cli.py` (after issue commands)

- [ ] **Step 1: Add `milestone-create` command**

```python
# ---------------------------------------------------------------------------
# Milestone Commands
# ---------------------------------------------------------------------------


@app.command()
def milestone_create(
    title: Annotated[str, typer.Option(help="Milestone title")],
    description: Annotated[str | None, typer.Option(help="Milestone description")] = None,
    due_date: Annotated[str | None, typer.Option(help="Due date (YYYY-MM-DD)")] = None,
) -> None:
    """Create a new milestone."""
    data: dict[str, Any] = {"title": title}
    if description:
        data["description"] = description
    if due_date:
        data["due_date"] = due_date

    try:
        resp: dict[str, Any] = api_request("projects/:id/milestones", method="POST", data=data)
    except GitLabAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)

    ms = Milestone.model_validate(resp)
    print(f"Created milestone #{ms.iid}")
    print(ms.display())
```

- [ ] **Step 2: Add `milestone-update` command**

```python
@app.command()
def milestone_update(
    iid: Annotated[int, typer.Argument(help="Milestone IID")],
    title: Annotated[str | None, typer.Option(help="New title")] = None,
    description: Annotated[str | None, typer.Option(help="New description")] = None,
    due_date: Annotated[str | None, typer.Option(help="Due date (YYYY-MM-DD)")] = None,
    state: Annotated[MilestoneState | None, typer.Option(help="State: active or closed")] = None,
) -> None:
    """Update an existing milestone."""
    data: dict[str, Any] = {}
    if title:
        data["title"] = title
    if description is not None:
        data["description"] = description
    if due_date is not None:
        data["due_date"] = due_date
    if state:
        data["state_event"] = "close" if state == MilestoneState.CLOSED else "activate"

    if not data:
        print("Nothing to update — provide at least one option.")
        return

    try:
        resp: dict[str, Any] = api_request(f"projects/:id/milestones/{iid}", method="PUT", data=data)
    except GitLabAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)

    ms = Milestone.model_validate(resp)
    print(f"Updated milestone #{ms.iid}")
    print(ms.display())
```

- [ ] **Step 3: Add `milestone-list` command**

```python
@app.command()
def milestone_list(
    all_projects: AllProjectsOpt = False,
    state: Annotated[str | None, typer.Option(help="Filter by state (active, closed)")] = None,
    search: Annotated[str | None, typer.Option(help="Search in title")] = None,
) -> None:
    """List milestones, optionally across all configured projects."""
    params: dict[str, str] = {}
    if state:
        params["state"] = state
    if search:
        params["search"] = search

    if all_projects:
        results = _for_each_project("projects/:id/milestones", params)
        found = False
        for project_id, milestones_data in results:
            if not milestones_data:
                continue
            if found:
                print()
            print(f"{project_id}:")
            for item in milestones_data:
                ms = Milestone.model_validate(item)
                print(f"  {ms.display()}")
            found = True
        if not found:
            print("No milestones found.")
    else:
        query = "?" + urllib.parse.urlencode(params) if params else ""
        try:
            resp: list[dict[str, Any]] = api_request(f"projects/:id/milestones{query}")
        except GitLabAPIError as e:
            print(f"Error: {e}", file=sys.stderr)
            raise typer.Exit(code=1)

        if not resp:
            print("No milestones found.")
            return

        for item in resp:
            ms = Milestone.model_validate(item)
            print(ms.display())
            print()
```

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/gitlab/gitlab_cli.py
git commit -m "[feat] Add milestone-create, milestone-update, milestone-list commands"
```

---

## Task 9: Implement `milestone-report`

**Files:**
- Modify: `.claude/skills/gitlab/gitlab_cli.py` (after milestone-list)

- [ ] **Step 1: Add `milestone-report` command**

```python
@app.command()
def milestone_report(
    title: Annotated[str, typer.Argument(help="Milestone title to report on")],
) -> None:
    """Aggregated milestone report across all configured projects.

    Shows progress stats and issue breakdown per repo for the given milestone title.
    """
    if not _config or not _config.projects:
        print("Error: No projects configured. Create config/gitlab.yaml.", file=sys.stderr)
        raise typer.Exit(code=1)

    reports: list[MilestoneReport] = []
    for name, proj in _config.projects.items():
        encoded = urllib.parse.quote(proj.project_id, safe="")
        headers = {"PRIVATE-TOKEN": _token}

        # Find milestone by title in this project
        ms_url = f"{_base_url}/api/v4/projects/{encoded}/milestones?title={urllib.parse.quote(title)}"
        req = urllib.request.Request(ms_url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, context=SSL_CTX) as resp:
                ms_data: list[dict[str, Any]] = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            print(f"warning: {proj.project_id}: {e.code} {e.reason} -- skipped", file=sys.stderr)
            continue

        if not ms_data:
            continue

        ms = Milestone.model_validate(ms_data[0])

        # Fetch issues for this milestone
        issues_url = f"{_base_url}/api/v4/projects/{encoded}/issues?milestone={urllib.parse.quote(title)}&per_page=100"
        req = urllib.request.Request(issues_url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, context=SSL_CTX) as resp:
                issues_data: list[dict[str, Any]] = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            print(f"warning: {proj.project_id}: could not fetch issues: {e.code} -- skipped", file=sys.stderr)
            continue

        issues = [Issue.model_validate(i) for i in issues_data]
        reports.append(MilestoneReport(project=proj.project_id, milestone=ms, issues=issues))

    if not reports:
        print(f"No projects have milestone '{title}'.")
        return

    total_issues = sum(r.total_count for r in reports)
    total_closed = sum(r.closed_count for r in reports)
    total_pct = (total_closed / total_issues * 100) if total_issues else 0

    print(f"Milestone: {title}\n")
    for report in reports:
        print(report.display())
        print()
    print(f"  Total: {total_closed}/{total_issues} closed ({total_pct:.0f}%)")
```

- [ ] **Step 2: Test manually**

```bash
uv run .claude/skills/gitlab/gitlab_cli.py milestone-report "v0.1.0" --config-path config/gitlab.yaml
```

Expected: Shows the v0.1.0 milestone report for claude-boy (and any other configured repos that have it).

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/gitlab/gitlab_cli.py
git commit -m "[feat] Add milestone-report with cross-repo aggregation"
```

---

## Task 10: Create example config file

**Files:**
- Create: `config/gitlab.yaml.example`

- [ ] **Step 1: Create the example config**

Create `config/gitlab.yaml.example`:

```yaml
# GitLab project management config
# Copy to config/gitlab.yaml and adjust for your projects.
#
# Used by: uv run .claude/skills/gitlab/gitlab_cli.py
# Required for: --all-projects flag, milestone-report command

default_instance: git.urieljsc.com

projects:
  claude-boy:
    project_id: "zariel/claude-boy"
  # Add more projects:
  # my-other-repo:
  #   project_id: "zariel/my-other-repo"
```

- [ ] **Step 2: Commit**

```bash
git add config/gitlab.yaml.example
git commit -m "[chore] Add gitlab.yaml.example config template"
```

---

## Task 11: Update SKILL.md

**Files:**
- Modify: `.claude/skills/gitlab/SKILL.md`

- [ ] **Step 1: Replace SKILL.md with updated content**

Replace the full content of `.claude/skills/gitlab/SKILL.md` with:

```markdown
---
name: gitlab
description: >
  Post inline comments, list discussions, reply to threads, and batch-comment on GitLab merge requests,
  AND manage issues, milestones, and cross-repo reporting via CLI. Use this skill whenever you need to
  add diff comments on specific file lines, read MR discussions with file positions, reply to discussion
  threads, post multiple review comments, create/update/list issues, manage milestones, or view milestone
  progress across repos. Even if the user doesn't say "gitlab" — if you're working with a GitLab repo
  (git remote points to a non-GitHub host) and need to interact with issues or MRs, use this skill.
  For basic MR operations (create, list, view, approve, merge, general comments, resolve) use `glab` CLI directly.
---

# GitLab CLI Skill

Manage MR discussions, issues, and milestones on GitLab using `gitlab_cli.py` via `uv run`.

This CLI covers what `glab` cannot do — inline (diff) comments, structured discussion listing, thread replies, batch commenting, cross-repo issue listing, and milestone reporting. For basic MR operations, use `glab` directly.

## Prerequisites

- **Auth**: `GITLAB_TOKEN` env var, or `glab auth login` (the CLI reads glab's stored token as fallback)
- **Project**: Auto-detected from `git remote origin`, or use `--project` with a named config entry or literal `group/repo` path
- **Config** (optional): `config/gitlab.yaml` for cross-repo operations. Copy from `config/gitlab.yaml.example`.
- Uses `uv run` with inline script dependencies (typer, pydantic, pyyaml, certifi)

## Config Setup

For cross-repo commands (`--all-projects`, `milestone-report`), create `config/gitlab.yaml`:

```yaml
default_instance: git.urieljsc.com

projects:
  claude-boy:
    project_id: "zariel/claude-boy"
  genbook:
    project_id: "zariel/genbook"
```

Config lookup order: `--config-path` flag > `./config/gitlab.yaml` > `~/Source/claude-boy/config/gitlab.yaml`

## Quick Reference

### MR Commands (unchanged)

| Command | What it does | Why not `glab`? |
|---------|--------------|-----------------|
| `inline-comment` | Post a comment on a specific file + line | `glab mr note` only does general comments |
| `batch-inline` | Post multiple inline comments at once | Not supported at all |
| `discussions` | List discussions with file positions + threads | `glab mr view -c` shows flat text only |
| `reply` | Reply to a discussion thread | `glab mr note` can't target a thread |

### Issue Commands

| Command | What it does | Cross-repo |
|---------|--------------|------------|
| `issue-create` | Create issue with labels, milestone, assignee, due date | No |
| `issue-get` | Get full issue details | No |
| `issue-update` | Update any issue field (title, labels, state, etc.) | No |
| `issue-list` | List/search issues with filters | Yes (`--all-projects`) |
| `issue-close` | Close an issue | No |
| `issue-reopen` | Reopen an issue | No |

### Milestone Commands

| Command | What it does | Cross-repo |
|---------|--------------|------------|
| `milestone-create` | Create milestone with due date | No |
| `milestone-update` | Update milestone (title, due date, state) | No |
| `milestone-list` | List milestones with filters | Yes (`--all-projects`) |
| `milestone-report` | Aggregated stats + issues per milestone | Yes (always) |

## Usage

All commands:

```bash
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py <command> [options]
```

### Issues

```bash
# Create an issue
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py issue-create \
  --title "[feat] Add auth endpoint" \
  --labels "feature,priority::high" \
  --milestone "v0.1.0" \
  --due-date "2026-05-01"

# Get issue details
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py issue-get 1

# Update an issue
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py issue-update 1 \
  --labels "feature,in-progress" --assignee cle

# List issues (single project)
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py issue-list --state opened

# List issues (all configured projects)
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py issue-list --all-projects --milestone "v0.1.0"

# Close / reopen
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py issue-close 1
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py issue-reopen 1
```

### Milestones

```bash
# Create a milestone
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py milestone-create \
  --title "v0.2.0" --due-date "2026-05-30"

# Update a milestone
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py milestone-update 1 \
  --due-date "2026-06-15"

# List milestones (all projects)
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py milestone-list --all-projects

# Aggregated report
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py milestone-report "v0.1.0"
```

### MR Inline Comments (existing)

```bash
# Post inline comment
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py inline-comment \
  --mr 20 --path src/service.py --line 42 \
  "This method should handle the None case"

# Batch inline comments
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py batch-inline --mr 20 \
  '[{"path": "src/auth.py", "line": 15, "body": "Missing validation"}]'

# List discussions
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py discussions --mr 20 --unresolved

# Reply to a discussion
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py reply \
  --mr 20 --discussion-id abc123 "Fixed in latest commit"
```

## Notes

- `issue-update --labels` **replaces** all labels (GitLab API behavior). Include all desired labels, not just additions.
- `--all-projects` requires `config/gitlab.yaml` with project entries.
- `milestone-report` always operates cross-repo. Repos without the milestone are silently skipped.
- Failed projects in cross-repo queries log a warning and continue (no full failure).

## Global Options

| Option | Description | Default |
|--------|-------------|---------|
| `--project` | Named config entry or literal `group/repo` path | Auto-detected from git remote |
| `--host` | GitLab hostname | Auto-detected from glab config |
| `--config-path` | Path to `gitlab.yaml` config | `./config/gitlab.yaml` |

## When to Use This vs `glab`

| Task | Use |
|------|-----|
| Create / list / view MRs | `glab mr create`, `glab mr list`, `glab mr view` |
| General comment on MR | `glab mr note 20 -m "LGTM"` |
| Approve / merge | `glab mr approve`, `glab mr merge` |
| View diff | `glab mr diff` |
| Resolve/unresolve thread | `glab mr note 20 --resolve <note-id>` |
| Time tracking | `glab api` with time tracking endpoints |
| **Inline comment on file line** | **This CLI** |
| **Batch inline comments** | **This CLI** |
| **List discussions with positions** | **This CLI** |
| **Reply to a thread** | **This CLI** |
| **Issue CRUD** | **This CLI** |
| **Cross-repo issue listing** | **This CLI** |
| **Milestone management** | **This CLI** |
| **Milestone report** | **This CLI** |
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/gitlab/SKILL.md
git commit -m "[docs] Update gitlab SKILL.md with issue and milestone commands"
```

---

## Task 12: Update skill-invocation.md triggers

**Files:**
- Modify: `.claude/rules/skill-invocation.md`

- [ ] **Step 1: Add new trigger rows**

In `.claude/rules/skill-invocation.md`, in the Natural Language Triggers table, add these rows after the existing entries:

```markdown
| "create gitlab issue", "new issue", "file an issue" | `gitlab` | GitLab issue management |
| "list issues", "show issues across repos", "issues for milestone" | `gitlab` | Issue listing/filtering |
| "create milestone", "new milestone" | `gitlab` | Milestone creation |
| "milestone report", "milestone progress", "show milestones" | `gitlab` | Milestone reporting |
| "close issue", "reopen issue", "update issue" | `gitlab` | Issue state management |
```

- [ ] **Step 2: Commit**

```bash
git add .claude/rules/skill-invocation.md
git commit -m "[docs] Add gitlab issue/milestone triggers to skill-invocation rules"
```

---

## Task 13: End-to-end verification

- [ ] **Step 1: Verify `--help` shows all commands**

```bash
uv run .claude/skills/gitlab/gitlab_cli.py --help
```

Expected: All 14 commands listed (4 existing MR + 6 issue + 4 milestone).

- [ ] **Step 2: Verify issue-get against real issue**

```bash
uv run .claude/skills/gitlab/gitlab_cli.py issue-get --project zariel/claude-boy 1
```

Expected: Shows issue #1 with title, labels, milestone, due date, description.

- [ ] **Step 3: Verify milestone-list**

```bash
uv run .claude/skills/gitlab/gitlab_cli.py milestone-list --project zariel/claude-boy
```

Expected: Shows v0.1.0 milestone with due date.

- [ ] **Step 4: Create `config/gitlab.yaml` and test cross-repo**

```bash
cp config/gitlab.yaml.example config/gitlab.yaml
uv run .claude/skills/gitlab/gitlab_cli.py milestone-report "v0.1.0" --config-path config/gitlab.yaml
```

Expected: Report showing claude-boy's v0.1.0 progress with issue breakdown.

- [ ] **Step 5: Verify existing MR commands still work**

```bash
uv run .claude/skills/gitlab/gitlab_cli.py --help | grep -E "inline-comment|batch-inline|discussions|reply"
```

Expected: All 4 MR commands still present.
