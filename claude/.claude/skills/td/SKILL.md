---
name: td
description: Use when the user says td, todoist, Todoist task, add task, create todo, capture an action item, or wants a task saved with project/section routing, a concise title, and full description.
---

# TD - Todoist Task Capture

Create Todoist tasks with a short task header and complete description, routed to the right project and section.

## Tool

Use the bundled helper:

```bash
uv run /home/cle/.claude/skills/td/scripts/td_cli.py <command>
```

The helper reads `TODOIST_API_TOKEN` or `TODOIST_API_KEY`. Never print token values.

## Workflow

1. Extract a concise task header from the user request. Keep it action-oriented and short.
2. Preserve the full details in the task description: context, links, commands, acceptance notes, and any constraints the user gave.
3. Resolve the destination:
   - If project and section are stated, pass both explicitly.
   - If only a section is stated, resolve the project first when possible because section names can repeat.
   - If destination is ambiguous, list projects/sections and ask one direct question.
4. Create the task with `add`.
5. Report the created task title and URL. Do not echo secrets.

## Commands

List projects:

```bash
uv run /home/cle/.claude/skills/td/scripts/td_cli.py list-projects
```

List sections, optionally scoped to a project:

```bash
uv run /home/cle/.claude/skills/td/scripts/td_cli.py list-sections --project "Area"
```

Create a task:

```bash
uv run /home/cle/.claude/skills/td/scripts/td_cli.py add \
  --project "Area" \
  --section "Home" \
  --header "Fix backup warning" \
  --details "Investigate the failed snapshot and record the result."
```

Useful options:

- `--details-file <path>` reads a longer Markdown description from a file; `-` reads stdin.
- `--label <name>` can be repeated.
- `--due "tomorrow"` passes Todoist natural-language due text.
- `--priority 1..4` sets Todoist priority.
- `--dry-run` prints the API payload without creating a task.

## Routing Rules

- Prefer exact project and section names from the user.
- Use project-scoped section lookup when a section name may exist in multiple projects.
- If the request has no obvious Todoist destination, inspect live destinations with `list-projects` and `list-sections`.
- Do not hard-code project or section IDs in notes, prompts, or commits; resolve them at runtime.
