# Design: `mrs` command for gitlab_cli.py

## Summary

Add a `mrs` command to `gitlab_cli.py` that reads a YAML config of important repos and displays all open merge requests grouped by repo.

## Config

`repos.yaml` lives next to `gitlab_cli.py` at `/home/cle/.claude/skills/gitlab/repos.yaml`.

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

Plain list of `group/project` paths. No nesting or grouping metadata — the group is already in the path.

## New Pydantic Model

```python
class MRSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")
    iid: int
    title: str
    author: Author
    updated_at: str

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> MRSummary:
        return cls.model_validate(data)

    def display(self) -> str:
        date = self.updated_at[:10]
        return f"!{self.iid:<5} {self.author.username:<12} {date}  {self.title}"
```

## Command Signature

```python
@app.command()
def mrs() -> None:
```

No arguments. Reads `repos.yaml`, iterates over each repo, calls the GitLab API, and prints grouped output.

## API Call

For each repo in the config:
```
GET /api/v4/projects/{url_encoded_path}/merge_requests?state=opened&per_page=100
```

This bypasses the global `_project_id` — each repo is URL-encoded independently.

## Output Format

```
=== uriel/genbook-mono (3 open) ===
!24   hoangi19     2026-04-03  Draft: [GGA-130] feat: add canonical schema...
!22   cle          2026-04-01  feat: Add Airbyte post-process pipeline...
!15   cle          2026-03-28  Draft: [GGA-118] feat: implement canonical_amz_order_line

=== uriel/imagination ===
No open merge requests.

Total: 8 open MRs across 8 repos
```

- Repos with no open MRs show a one-liner (confirms the repo was checked)
- Summary line at end with total count
- Title truncated at 80 chars if needed

## Error Handling

- Missing `repos.yaml`: print error with expected path and exit
- API error for one repo: print warning, continue to next repo (don't abort the whole scan)
- Invalid YAML: print parse error and exit

## Dependencies

Add `pyyaml` to the inline script metadata (`# dependencies = ["certifi", "typer", "pydantic", "pyyaml"]`).

## Changes to Existing Code

- Add `pyyaml` to script dependencies
- Add `MRSummary` model
- Add `ReposConfig` model to parse the YAML
- Add `mrs` command
- The `mrs` command calls `api_request` directly but overrides `_project_id` per repo — or more cleanly, URL-encodes each repo path inline and calls the API path with it substituted directly (no `:id` placeholder)

## What Does NOT Change

- Existing commands (`discussions`, `inline-comment`, `reply`, `batch-inline`) unchanged
- Global `--project` / `--host` options still work for existing commands
- Auth flow unchanged — `mrs` reuses the same token
