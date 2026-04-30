# `mrs` Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `mrs` command to `gitlab_cli.py` that lists all open MRs across configured repos, grouped by repo.

**Architecture:** Read a YAML config listing repo paths, iterate over each, query the GitLab MR API, and print grouped output. Reuses existing auth and API infrastructure in `gitlab_cli.py`.

**Tech Stack:** Python 3.10+, typer, pydantic, pyyaml, urllib (existing)

---

### File Map

- Modify: `/home/cle/.claude/skills/gitlab/gitlab_cli.py` — add dependency, models, and command
- Create: `/home/cle/.claude/skills/gitlab/repos.yaml` — repo list config
- Modify: `/home/cle/.claude/skills/gitlab/SKILL.md` — document new command

---

### Task 1: Create `repos.yaml` config file

**Files:**
- Create: `/home/cle/.claude/skills/gitlab/repos.yaml`

- [ ] **Step 1: Write the config file**

```yaml
repos:
  - uriel/genbook-mono
  - uriel/uriel
  - uriel/imagination
  - uriel/uriel2
  - zariel/claude-boy
  - zariel/imagination
  - devops/headscale
  - devops/ansible
```

- [ ] **Step 2: Commit**

```bash
git -C /home/cle/.claude/skills/gitlab add repos.yaml
git -C /home/cle/.claude/skills/gitlab commit -m "feat: add repos.yaml config for mrs command"
```

---

### Task 2: Add `pyyaml` dependency and `ReposConfig` model

**Files:**
- Modify: `/home/cle/.claude/skills/gitlab/gitlab_cli.py:1-5` (script metadata)
- Modify: `/home/cle/.claude/skills/gitlab/gitlab_cli.py` (add model after `MRInfo` class, ~line 153)

- [ ] **Step 1: Add pyyaml to inline script dependencies**

Change line 4 from:
```python
# dependencies = ["certifi", "typer", "pydantic"]
```
to:
```python
# dependencies = ["certifi", "typer", "pydantic", "pyyaml"]
```

- [ ] **Step 2: Add yaml import**

Add after `import urllib.request` (line 27):
```python
from pathlib import Path

import yaml
```

Note: `yaml` comes from pyyaml. `Path` is for locating `repos.yaml` relative to the script.

- [ ] **Step 3: Add `ReposConfig` model**

Add after the `MRInfo` class (after line 153):

```python
class ReposConfig(BaseModel):
    """Config for the mrs command — list of repo paths to scan."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    repos: list[str]
```

- [ ] **Step 4: Verify syntax**

Run: `uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py --help`
Expected: Help output showing all commands (no import errors)

- [ ] **Step 5: Commit**

```bash
git -C /home/cle/.claude/skills/gitlab add gitlab_cli.py
git -C /home/cle/.claude/skills/gitlab commit -m "feat: add pyyaml dep and ReposConfig model"
```

---

### Task 3: Add `MRSummary` model

**Files:**
- Modify: `/home/cle/.claude/skills/gitlab/gitlab_cli.py` (add after `ReposConfig`)

- [ ] **Step 1: Add `MRSummary` model**

Add after `ReposConfig`:

```python
class MRSummary(BaseModel):
    """Summary of an open merge request for the mrs dashboard."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    iid: int
    title: str
    author: Author
    updated_at: str

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> MRSummary:
        return cls.model_validate(data)

    def display(self) -> str:
        date = self.updated_at[:10]
        title = self.title[:80] if len(self.title) > 80 else self.title
        return f"!{self.iid:<5} {self.author.username:<12} {date}  {title}"
```

- [ ] **Step 2: Verify syntax**

Run: `uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py --help`
Expected: Help output, no errors

- [ ] **Step 3: Commit**

```bash
git -C /home/cle/.claude/skills/gitlab add gitlab_cli.py
git -C /home/cle/.claude/skills/gitlab commit -m "feat: add MRSummary model"
```

---

### Task 4: Implement the `mrs` command

**Files:**
- Modify: `/home/cle/.claude/skills/gitlab/gitlab_cli.py` (add command after `batch_inline`)

- [ ] **Step 1: Add the `mrs` command**

Add after the `batch_inline` command (before `if __name__ == "__main__":`):

```python
@app.command()
def mrs() -> None:
    """List open merge requests across all configured repos."""
    config_path = Path(__file__).parent / "repos.yaml"
    if not config_path.exists():
        print(f"Error: Config not found: {config_path}", file=sys.stderr)
        raise typer.Exit(code=1)

    try:
        raw = yaml.safe_load(config_path.read_text())
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML in {config_path}: {e}", file=sys.stderr)
        raise typer.Exit(code=1)

    config = ReposConfig.model_validate(raw)
    total = 0

    for repo_path in config.repos:
        encoded = urllib.parse.quote(repo_path, safe="")
        try:
            resp: list[dict[str, Any]] = api_request(
                f"projects/{encoded}/merge_requests?state=opened&per_page=100",
            )
        except GitLabAPIError as e:
            print(f"=== {repo_path} ===")
            print(f"  Error: {e}")
            print()
            continue

        mrs_list = [MRSummary.from_response(item) for item in resp]

        if mrs_list:
            print(f"=== {repo_path} ({len(mrs_list)} open) ===")
            for mr in mrs_list:
                print(mr.display())
        else:
            print(f"=== {repo_path} ===")
            print("No open merge requests.")
        print()
        total += len(mrs_list)

    print(f"Total: {total} open MRs across {len(config.repos)} repos")
```

- [ ] **Step 2: Verify the command appears in help**

Run: `uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py --help`
Expected: `mrs` listed among the commands

- [ ] **Step 3: Test the command live**

Run: `uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py mrs`
Expected: Grouped output showing open MRs for each configured repo, with a total count at the end.

- [ ] **Step 4: Commit**

```bash
git -C /home/cle/.claude/skills/gitlab add gitlab_cli.py
git -C /home/cle/.claude/skills/gitlab commit -m "feat: add mrs command to list open MRs across repos"
```

---

### Task 5: Update SKILL.md documentation

**Files:**
- Modify: `/home/cle/.claude/skills/gitlab/SKILL.md`

- [ ] **Step 1: Add `mrs` to the quick reference table**

In the Quick Reference table, add a row:

```markdown
| `mrs` | List open MRs across all configured repos | `glab mr list` only works per-repo |
```

- [ ] **Step 2: Add usage section**

Add after the "List Discussions" section:

```markdown
### List Open MRs Across Repos

```bash
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py mrs
```

Reads `repos.yaml` (next to the script) for the list of repos to scan. Edit that file to add or remove repos.
```

- [ ] **Step 3: Update the "When to Use This vs glab" table**

Add a row:

```markdown
| **List MRs across multiple repos** | **This CLI** |
```

- [ ] **Step 4: Commit**

```bash
git -C /home/cle/.claude/skills/gitlab add SKILL.md
git -C /home/cle/.claude/skills/gitlab commit -m "docs: add mrs command to SKILL.md"
```
