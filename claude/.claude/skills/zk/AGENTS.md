# Agent Guide

This directory defines the personal Claude Code `zk` skill. Treat it as public
dotfiles: do not commit notebook contents, credentials, runtime state, caches, or
generated note data.

## Current Practice

- `/zk` means capture a note into both today's journal and a related topic note.
- Use a short, action-oriented title and preserve the user's full details.
- Prefer `zk_cli.py capture` for `/zk` captures:

```bash
uv run /home/cle/.claude/skills/zk/zk_cli.py capture \
  --title "Short header" \
  --related-note "topic-note" \
  --details "Full details"
```

- `capture` creates `journal/YYYY-MM-DD.md` and the related note if missing,
  appends under `## Notes`, and links both sides with `[[wiki-link]]` syntax.
- Use `--date YYYY-MM-DD` only when the user explicitly asks for a date other
  than today.
- If the related note is unclear, search before writing:

```bash
zk list --match "query" --notebook-dir /srv/selfhost/zk
```

## Source Of Truth

- `SKILL.md`: user-facing trigger and workflow instructions.
- `zk_cli.py`: deterministic note/todo operations.
- `test_zk_cli.py`: regression tests for capture behavior.
- `/srv/selfhost/zk`: live notebook path; this is data, not part of this repo.

## Editing Rules

- Check `git -C /home/cle/Source/dotfiles status --short` before editing.
- Do not touch unrelated dirty files, especially `codex/.codex/config.toml`.
- Add or update tests before changing `zk_cli.py` behavior.
- Keep `SKILL.md` concise; move deterministic behavior into `zk_cli.py`.
- Do not hard-code private note contents or copy notebook data into this skill.
- Do not commit `.pytest_cache`, `__pycache__`, or temporary notebooks.

## Verification

Run these after changes:

```bash
uv run --with pytest --with typer --with pydantic pytest /home/cle/.claude/skills/zk/test_zk_cli.py
python3 /home/cle/.codex/skills/.system/skill-creator/scripts/quick_validate.py /home/cle/.claude/skills/zk
python3 -m py_compile /home/cle/.claude/skills/zk/zk_cli.py
git -C /home/cle/Source/dotfiles diff --check -- claude/.claude/skills/zk
```
