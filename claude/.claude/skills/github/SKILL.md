---
name: github
description: >
  Manage GitHub pull requests, reviews, and comments via CLI. Use this skill whenever you need to
  create or update PRs, review code, add comments, reply to review threads, or list PRs.
  Even if the user doesn't mention "github" by name — if they want to manage PRs, do code review,
  or interact with pull requests, use this skill.
---

# GitHub PR CLI Skill

Manage GitHub pull requests using `github_cli.py` via `uv run`.

## Prerequisites

- `GITHUB_TOKEN` environment variable set (personal access token or installation token)
- Token needs `repo` scope for private repos, `public_repo` for public repos
- Uses `uv run` with inline script dependencies (typer, pydantic, certifi, pyjwt)

## Quick Reference

| Command | Description |
|---------|-------------|
| `create-pr` | Create a pull request |
| `update-pr` | Update an existing PR (title, body, state, base) |
| `list-prs` | List pull requests with filters |
| `get-pr` | Get PR details including changed files |
| `comments` | Get all comments on a PR |
| `comment` | Add a general or inline comment |
| `review` | Submit a review (APPROVE, REQUEST_CHANGES, COMMENT) |
| `review-comment` | Create an inline review comment on a file |
| `reply` | Reply to a review comment thread |
| `resolve` | Resolve or unresolve a review thread |

## Usage

All commands follow this pattern:

```bash
uv run /home/cle/.claude/skills/github/github_cli.py <command> [options]
```

Use `--help` on any command to see full option details and enum choices.

### Create a Pull Request

```bash
uv run /home/cle/.claude/skills/github/github_cli.py create-pr \
  --owner myorg --repo myrepo \
  --title "feat: add auth" \
  --head feature-auth --base main \
  --body "Adds JWT authentication" \
  --draft
```

### Update a Pull Request

```bash
uv run /home/cle/.claude/skills/github/github_cli.py update-pr \
  --owner myorg --repo myrepo --number 42 \
  --title "feat: updated title" \
  --state closed
```

### List Pull Requests

```bash
uv run /home/cle/.claude/skills/github/github_cli.py list-prs \
  --owner myorg --repo myrepo \
  --state open --sort updated --direction desc \
  --base main --page 1 --page-size 10
```

### Get PR Details

Returns PR metadata and list of changed files with additions/deletions.

```bash
uv run /home/cle/.claude/skills/github/github_cli.py get-pr \
  --owner myorg --repo myrepo --number 42
```

### Get PR Comments

Fetches both general issue comments and inline review comments.

```bash
uv run /home/cle/.claude/skills/github/github_cli.py comments \
  --owner myorg --repo myrepo --number 42
```

### Add a Comment

General comment:

```bash
uv run /home/cle/.claude/skills/github/github_cli.py comment \
  --owner myorg --repo myrepo --number 42 \
  "Looks good, just one nit"
```

Inline comment on a file/line:

```bash
uv run /home/cle/.claude/skills/github/github_cli.py comment \
  --owner myorg --repo myrepo --number 42 \
  "Consider using a constant here" \
  --path src/auth.py --line 15
```

### Submit a Review

```bash
uv run /home/cle/.claude/skills/github/github_cli.py review \
  --owner myorg --repo myrepo --number 42 \
  --event APPROVE --body "LGTM!"
```

Events: `APPROVE`, `REQUEST_CHANGES`, `COMMENT`

### Create Inline Review Comment

```bash
uv run /home/cle/.claude/skills/github/github_cli.py review-comment \
  --owner myorg --repo myrepo --number 42 \
  --path src/auth.py --line 25 \
  "This should handle the None case" \
  --side RIGHT
```

### Reply to a Review Comment

```bash
uv run /home/cle/.claude/skills/github/github_cli.py reply \
  --owner myorg --repo myrepo --number 42 \
  --comment-id 123456 \
  "Fixed in the latest commit"
```

### Resolve a Review Thread

Resolve:

```bash
uv run /home/cle/.claude/skills/github/github_cli.py resolve \
  --owner myorg --repo myrepo --number 42 \
  --comment-id 123456
```

Unresolve:

```bash
uv run /home/cle/.claude/skills/github/github_cli.py resolve \
  --owner myorg --repo myrepo --number 42 \
  --comment-id 123456 --unresolve
```

Note: Resolve uses GitHub's GraphQL API to find the thread by comment ID and toggle resolution.
