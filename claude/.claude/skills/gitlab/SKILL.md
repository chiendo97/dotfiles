---
name: gitlab
description: >
  Post inline comments, list discussions, reply to threads, and batch-comment on GitLab merge requests
  via CLI. Use this skill whenever you need to add diff comments on specific file lines, read MR
  discussions with file positions, reply to discussion threads, or post multiple review comments at
  once on a GitLab MR. Even if the user doesn't say "gitlab" — if you're working with a GitLab repo
  (git remote points to a non-GitHub host) and need to comment on an MR, use this skill. For basic MR
  operations (create, list, view, approve, merge, general comments, resolve) use `glab` CLI directly.
---

# GitLab MR CLI Skill

Post inline diff comments, list discussions, and reply to threads on GitLab MRs using `gitlab_cli.py` via `uv run`.

This CLI covers what `glab` cannot do — inline (diff) comments, structured discussion listing, thread replies, and batch commenting. For everything else, use `glab` directly.

## Prerequisites

- **Auth**: `GITLAB_TOKEN` env var, or `glab auth login` (the CLI reads glab's stored token as fallback)
- **Project**: Auto-detected from `git remote origin` — no need to specify unless working outside a repo
- Uses `uv run` with inline script dependencies (typer, pydantic, certifi)

## Quick Reference

| Command | What it does | Why not `glab`? |
|---------|--------------|-----------------|
| `inline-comment` | Post a comment on a specific file + line | `glab mr note` only does general comments |
| `batch-inline` | Post multiple inline comments at once | Not supported at all |
| `discussions` | List discussions with file positions + threads | `glab mr view -c` shows flat text only |
| `reply` | Reply to a discussion thread | `glab mr note` can't target a thread |
| `mrs` | List open MRs across all configured repos | `glab mr list` only works per-repo |

## Usage

All commands follow this pattern:

```bash
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py <command> [options]
```

### Post an Inline Comment

```bash
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py inline-comment \
  --mr 20 --path src/service.py --line 42 \
  "This method should handle the None case"
```

The CLI auto-fetches the MR's `diff_refs` (base/head/start SHAs) so you only need the file path and line number.

### Batch Inline Comments

Post multiple comments in one call. Pass a JSON array as the argument:

```bash
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py batch-inline --mr 20 \
  '[{"path": "src/auth.py", "line": 15, "body": "Missing validation"}, {"path": "src/db.py", "line": 88, "body": "Connection leak"}]'
```

### List Discussions

```bash
# All discussions
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py discussions --mr 20

# Only inline (diff) discussions
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py discussions --mr 20 --inline-only

# Only unresolved
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py discussions --mr 20 --unresolved
```

### List Open MRs Across Repos

```bash
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py mrs
```

Reads `repos.yaml` (next to the script) for the list of repos to scan. Edit that file to add or remove repos.

### Reply to a Discussion

```bash
uv run /home/cle/.claude/skills/gitlab/gitlab_cli.py reply \
  --mr 20 --discussion-id abc123def456 \
  "Fixed in the latest commit"
```

## When to Use This vs `glab`

| Task | Use |
|------|-----|
| Create / list / view MRs | `glab mr create`, `glab mr list`, `glab mr view` |
| General comment on MR | `glab mr note 20 -m "LGTM"` |
| Approve / merge | `glab mr approve`, `glab mr merge` |
| View diff | `glab mr diff` |
| Resolve/unresolve thread | `glab mr note 20 --resolve <note-id>` |
| **Inline comment on file line** | **This CLI** |
| **Batch inline comments** | **This CLI** |
| **List discussions with positions** | **This CLI** |
| **Reply to a thread** | **This CLI** |
| **List MRs across multiple repos** | **This CLI** |

## Options

All commands accept these global options:

| Option | Description | Default |
|--------|-------------|---------|
| `--project` | Project path (group/repo) | Auto-detected from git remote |
| `--host` | GitLab hostname | Auto-detected from glab config |
