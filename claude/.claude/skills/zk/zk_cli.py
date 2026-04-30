#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["typer", "pydantic"]
# ///
"""ZK Todo CLI — line-level todo operations for a Zettelkasten notebook.

Handles listing, adding, completing, and summarizing todos across markdown
notes. Designed to complement the zk CLI which handles note-level operations.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel

# =============================================================================
# Constants
# =============================================================================

DEFAULT_NOTEBOOK_DIR = Path("/home/cle/Source/selfhost/zk")
TODO_OPEN_RE = re.compile(r"^(\s*)-\s*\[ \]\s*(.*)")
TODO_DONE_RE = re.compile(r"^(\s*)-\s*\[x\]\s*(.*)", re.IGNORECASE)
TASKS_HEADING_RE = re.compile(r"^##\s+Tasks\s*$")

# =============================================================================
# Models
# =============================================================================


class TodoItem(BaseModel):
    file: str
    line: int
    text: str
    done: bool

    def display(self, relative_to: Path) -> str:
        rel = Path(self.file).relative_to(relative_to)
        marker = "[x]" if self.done else "[ ]"
        return f"{rel}:{self.line}  {marker} {self.text}"


class TodoSummaryGroup(BaseModel):
    file: str
    todos: list[TodoItem]

    def display(self, relative_to: Path) -> str:
        rel = Path(self.file).relative_to(relative_to)
        stem = rel.with_suffix("").as_posix()
        lines = [f"{stem} ({len(self.todos)} todos)"]
        for todo in self.todos:
            lines.append(f"  - {todo.text}")
        return "\n".join(lines)


# =============================================================================
# Core logic
# =============================================================================


def find_todos(
    notebook_dir: Path,
    *,
    filter_prefix: str | None = None,
    include_open: bool = True,
    include_done: bool = False,
) -> list[TodoItem]:
    """Walk markdown files and extract todo items."""
    glob_pattern = f"{filter_prefix}*.md" if filter_prefix else "*.md"
    todos: list[TodoItem] = []

    # Collect files from root and subdirectories matching the pattern
    files = sorted(notebook_dir.glob(glob_pattern)) + sorted(
        notebook_dir.glob(f"**/{glob_pattern}")
    )
    # Deduplicate while preserving order
    seen: set[Path] = set()
    unique_files: list[Path] = []
    for f in files:
        resolved = f.resolve()
        if resolved not in seen and f.is_file():
            seen.add(resolved)
            unique_files.append(f)

    for filepath in unique_files:
        lines = filepath.read_text().splitlines()
        for i, line in enumerate(lines, start=1):
            if include_open:
                m = TODO_OPEN_RE.match(line)
                if m:
                    todos.append(
                        TodoItem(
                            file=str(filepath), line=i, text=m.group(2).strip(), done=False
                        )
                    )
            if include_done:
                m = TODO_DONE_RE.match(line)
                if m:
                    todos.append(
                        TodoItem(
                            file=str(filepath), line=i, text=m.group(2).strip(), done=True
                        )
                    )

    return todos


def resolve_note_path(notebook_dir: Path, note: str) -> Path:
    """Resolve a note argument to a file path, adding .md if needed."""
    path = notebook_dir / note
    if not path.suffix:
        path = path.with_suffix(".md")
    if not path.exists():
        typer.echo(f"Error: note not found: {path}", err=True)
        raise typer.Exit(1)
    return path


def find_tasks_section_end(lines: list[str]) -> int | None:
    """Find the line index after the ## Tasks section content.

    Returns the index where a new todo should be inserted, or None if
    no ## Tasks heading exists.
    """
    tasks_start: int | None = None
    for i, line in enumerate(lines):
        if TASKS_HEADING_RE.match(line):
            tasks_start = i
            break

    if tasks_start is None:
        return None

    # Find the last non-empty line in the Tasks section (before next heading or EOF)
    insert_at = tasks_start + 1
    for i in range(tasks_start + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("## ") or stripped.startswith("# "):
            break
        if stripped:
            insert_at = i + 1

    return insert_at


# =============================================================================
# CLI
# =============================================================================

app = typer.Typer(help="Todo operations for a Zettelkasten notebook.")

NotebookDirOpt = Annotated[
    Path,
    typer.Option("--notebook-dir", "-d", help="Path to the zk notebook."),
]


@app.command("list")
def list_cmd(
    notebook_dir: NotebookDirOpt = DEFAULT_NOTEBOOK_DIR,
    filter_prefix: Annotated[
        str | None, typer.Option("--filter", "-f", help="Filename prefix filter.")
    ] = None,
    done: Annotated[bool, typer.Option("--done", help="Show completed todos.")] = False,
    all_: Annotated[
        bool, typer.Option("--all", help="Show both open and completed todos.")
    ] = False,
) -> None:
    """List todos across notes."""
    include_open = not done or all_
    include_done = done or all_

    todos = find_todos(
        notebook_dir,
        filter_prefix=filter_prefix,
        include_open=include_open,
        include_done=include_done,
    )

    if not todos:
        typer.echo("No todos found.")
        raise typer.Exit(0)

    for todo in todos:
        typer.echo(todo.display(notebook_dir))


@app.command()
def add(
    note: Annotated[str, typer.Argument(help="Note file (e.g. genbook-api or journal/2026-04-04)")],
    text: Annotated[str, typer.Argument(help="Todo text to add.")],
    notebook_dir: NotebookDirOpt = DEFAULT_NOTEBOOK_DIR,
) -> None:
    """Add a todo to a note."""
    path = resolve_note_path(notebook_dir, note)
    lines = path.read_text().splitlines()

    todo_line = f"- [ ] {text}"
    insert_at = find_tasks_section_end(lines)

    if insert_at is not None:
        lines.insert(insert_at, todo_line)
    else:
        # Append at end, with blank line separator if needed
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(todo_line)

    path.write_text("\n".join(lines) + "\n")
    typer.echo(f"Added to {path.relative_to(notebook_dir)}:{insert_at or len(lines)}: {todo_line}")


@app.command()
def done(
    note: Annotated[str, typer.Argument(help="Note file path.")],
    line: Annotated[int, typer.Argument(help="Line number of the todo to mark done.")],
    notebook_dir: NotebookDirOpt = DEFAULT_NOTEBOOK_DIR,
) -> None:
    """Mark a todo as completed by file and line number."""
    path = resolve_note_path(notebook_dir, note)
    lines = path.read_text().splitlines()

    if line < 1 or line > len(lines):
        typer.echo(f"Error: line {line} out of range (file has {len(lines)} lines).", err=True)
        raise typer.Exit(1)

    target = lines[line - 1]
    if not TODO_OPEN_RE.match(target):
        typer.echo(f"Error: line {line} is not an open todo: {target.strip()!r}", err=True)
        raise typer.Exit(1)

    lines[line - 1] = target.replace("- [ ]", "- [x]", 1)
    path.write_text("\n".join(lines) + "\n")
    typer.echo(f"Done: {path.relative_to(notebook_dir)}:{line}  [x] {TODO_OPEN_RE.match(target).group(2).strip()}")  # type: ignore[union-attr]


@app.command()
def summary(
    notebook_dir: NotebookDirOpt = DEFAULT_NOTEBOOK_DIR,
    filter_prefix: Annotated[
        str | None, typer.Option("--filter", "-f", help="Filename prefix filter.")
    ] = None,
) -> None:
    """Summarize open todos grouped by note."""
    todos = find_todos(notebook_dir, filter_prefix=filter_prefix, include_open=True)

    if not todos:
        typer.echo("No open todos found.")
        raise typer.Exit(0)

    # Group by file
    groups: dict[str, list[TodoItem]] = {}
    for todo in todos:
        groups.setdefault(todo.file, []).append(todo)

    total_todos = 0
    for file, items in groups.items():
        group = TodoSummaryGroup(file=file, todos=items)
        typer.echo(group.display(notebook_dir))
        typer.echo("")
        total_todos += len(items)

    typer.echo(f"Total: {total_todos} open todos across {len(groups)} notes")


if __name__ == "__main__":
    app()
