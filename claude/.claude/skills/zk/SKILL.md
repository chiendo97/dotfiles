---
name: zk
description: >
  Manage Zettelkasten notes and todos via zk CLI and a todo helper script. Use this skill whenever
  the user mentions notes, todos, journal entries, tags, backlinks, knowledge base, zettelkasten,
  or wants to create/search/organize markdown notes. Even if the user doesn't mention "zk" by name —
  if they want to jot something down, check their open tasks, review what they worked on recently,
  add a todo, mark something done, or search their notes, use this skill.
---

# ZK — Zettelkasten Notes & Todos

Personal knowledge base managed by [zk](https://github.com/zk-org/zk) CLI. Notes are markdown files
with `[[wiki-link]]` syntax. Journal entries live in `journal/` with date-based filenames (`YYYY-MM-DD.md`).

## Environment

**Notebook path:** `/srv/selfhost/zk`

All `zk` commands must run from this directory or use `--notebook-dir /srv/selfhost/zk`.

## Note Operations (use zk CLI directly)

| Task | Command |
|------|---------|
| Create a note | `zk new --title "Title" -p --notebook-dir /srv/selfhost/zk` |
| Create today's journal | `zk new journal --title "$(date +%Y-%m-%d)" -p --notebook-dir /srv/selfhost/zk` |
| List recent notes | `zk list --sort created- --created-after 'last two weeks' --notebook-dir /srv/selfhost/zk` |
| Search note content | `zk list --match "query" --notebook-dir /srv/selfhost/zk` |
| Filter by tag | `zk list --tag <tag> --notebook-dir /srv/selfhost/zk` |
| List all tags | `zk tag list --notebook-dir /srv/selfhost/zk` |
| Find notes linking to X | `zk list --link-to <note>.md --notebook-dir /srv/selfhost/zk` |
| Find backlinks to X | `zk list --linked-by <note>.md --notebook-dir /srv/selfhost/zk` |
| Find related notes | `zk list --related <note>.md --notebook-dir /srv/selfhost/zk` |
| Find orphan notes | `zk list --orphan --notebook-dir /srv/selfhost/zk` |

### Templates

- **New notes** use `default.md` — adds YAML frontmatter with `tags` and `created` date
- **Journal entries** use `journal.md` — date heading, `## Tasks` section, `## Notes` section

### Note structure

- Root `.md` files are topic notes (projects, tools, etc.)
- `journal/` contains daily entries (`YYYY-MM-DD.md`)
- Tags use `#hashtag` syntax
- Links use `[[wiki-link]]` syntax

## Todo Operations (use zk_cli.py)

The todo CLI handles line-level operations that need precision — listing with line numbers,
adding to the right section, and toggling checkboxes unambiguously.

**Base command:**
```bash
uv run /home/cle/.claude/skills/zk/zk_cli.py <command> [options]
```

### List todos

```bash
# All open todos
uv run /home/cle/.claude/skills/zk/zk_cli.py list

# Filter by filename prefix (e.g. all genbook notes)
uv run /home/cle/.claude/skills/zk/zk_cli.py list --filter genbook

# Specific note
uv run /home/cle/.claude/skills/zk/zk_cli.py list --filter genbook-api

# Show completed todos
uv run /home/cle/.claude/skills/zk/zk_cli.py list --done

# Show both open and done
uv run /home/cle/.claude/skills/zk/zk_cli.py list --all
```

Output is a Rich table with file path and line number for each todo:
```
File            Line  Status  Task
genbook-api.md    12  open    Review PR #331
genbook-api.md    13  open    Check Axios dependency
```

### Add a todo

```bash
# Add to a specific note (under ## Tasks if present, else end of file)
uv run /home/cle/.claude/skills/zk/zk_cli.py add genbook-api "Review PR #332"

# .md extension is optional
uv run /home/cle/.claude/skills/zk/zk_cli.py add journal/2026-04-04 "Write summary"
```

### Mark a todo done

```bash
# By file and line number (from list output)
uv run /home/cle/.claude/skills/zk/zk_cli.py done genbook-api.md 12
```

Done items keep org-mode-style completion evidence on the same Markdown line:

```markdown
- [x] Review PR #331  CLOSED: [2026-05-14 Thu 22:39]
```

### Summary of open todos

```bash
# All notes
uv run /home/cle/.claude/skills/zk/zk_cli.py summary

# Filtered
uv run /home/cle/.claude/skills/zk/zk_cli.py summary --filter genbook
```

Output is a Rich table grouped by note with counts:
```
Note         Count  Tasks
genbook-api      3  - Review PR #331 — hoangi19
                    - Check Axios transitive dependency exposure
                    - Verify JE-to-ClickHouse migration progress

Total: 23 open todos across 12 notes
```

## When to use which

- **Creating/searching/browsing notes** — use `zk` CLI commands from the table above
- **Anything involving todos** (list, add, mark done, summarize) — use `zk_cli.py`
- **Reading or editing note content** — use Read/Edit tools directly on the markdown files in `/srv/selfhost/zk/`
