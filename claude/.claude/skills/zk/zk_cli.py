#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = ["typer", "pydantic", "rich"]
# ///
"""ZK Todo CLI — line-level todo operations for a Zettelkasten notebook.

Handles listing, adding, completing, and summarizing todos across markdown
notes. Designed to complement the zk CLI which handles note-level operations.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer
from pydantic import BaseModel
from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

# =============================================================================
# Constants
# =============================================================================

DEFAULT_NOTEBOOK_DIR = Path("/srv/selfhost/zk")
TODO_OPEN_RE = re.compile(r"^(\s*)-\s*\[ \]\s*(.*)")
TODO_DONE_RE = re.compile(r"^(\s*)-\s*\[x\]\s*(.*)", re.IGNORECASE)
ORG_CLOSED_RE = re.compile(r"\s+CLOSED:\s*\[[^\]]+\]\s*$")
TASKS_HEADING_RE = re.compile(r"^##\s+Tasks\s*$")
console = Console(highlight=False)
error_console = Console(stderr=True, highlight=False)

# =============================================================================
# Models
# =============================================================================


class TodoItem(BaseModel):
    file: str
    line: int
    text: str
    done: bool


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
        print_error(f"note not found: {path}")
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


def format_org_closed_timestamp() -> str:
    """Return an org-mode style CLOSED timestamp in the local timezone."""
    return datetime.now().astimezone().strftime("%Y-%m-%d %a %H:%M")


def mark_todo_done_line(line: str) -> tuple[str, str, str]:
    """Mark an open todo line done and append a CLOSED timestamp."""
    match = TODO_OPEN_RE.match(line)
    if match is None:
        raise ValueError("line is not an open todo")

    indent = match.group(1)
    text = ORG_CLOSED_RE.sub("", match.group(2).rstrip()).rstrip()
    closed_at = format_org_closed_timestamp()
    return f"{indent}- [x] {text}  CLOSED: [{closed_at}]", text, closed_at


def render_todo_table(todos: list[TodoItem], relative_to: Path) -> None:
    """Render todos as a compact Rich table."""
    table = Table(title="Todos", box=box.SIMPLE_HEAVY)
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Line", justify="right", style="magenta", no_wrap=True)
    table.add_column("Status", no_wrap=True)
    table.add_column("Task")

    for todo in todos:
        rel = Path(todo.file).relative_to(relative_to)
        status = Text("done", style="green") if todo.done else Text("open", style="yellow")
        table.add_row(rel.as_posix(), str(todo.line), status, Text(todo.text))

    console.print(table)


def render_summary_table(groups: dict[str, list[TodoItem]], relative_to: Path) -> None:
    """Render open todos grouped by note."""
    table = Table(title="Open Todos", box=box.SIMPLE_HEAVY)
    table.add_column("Note", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right", style="magenta", no_wrap=True)
    table.add_column("Tasks")

    total_todos = 0
    for file, todos in groups.items():
        rel = Path(file).relative_to(relative_to).with_suffix("").as_posix()
        task_text = Text("\n".join(f"- {todo.text}" for todo in todos))
        table.add_row(rel, str(len(todos)), task_text)
        total_todos += len(todos)

    console.print(table)
    console.print(
        Text(
            f"Total: {total_todos} open todos across {len(groups)} notes",
            style="bold",
        )
    )


def print_success(prefix: str, location: str, text: str) -> None:
    message = Text(f"{prefix}: ", style="green")
    message.append(location, style="cyan")
    message.append(f"  {text}")
    console.print(message)


def print_error(message: str) -> None:
    output = Text("Error: ", style="red bold")
    output.append(message)
    error_console.print(output)


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
        console.print("[yellow]No todos found.[/yellow]")
        raise typer.Exit(0)

    render_todo_table(todos, notebook_dir)


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
        line_number = insert_at + 1
    else:
        # Append at end, with blank line separator if needed
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(todo_line)
        line_number = len(lines)

    path.write_text("\n".join(lines) + "\n")
    print_success(
        "Added",
        f"{path.relative_to(notebook_dir)}:{line_number}",
        todo_line,
    )


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
        print_error(f"line {line} out of range (file has {len(lines)} lines).")
        raise typer.Exit(1)

    target = lines[line - 1]
    if not TODO_OPEN_RE.match(target):
        print_error(f"line {line} is not an open todo: {target.strip()!r}")
        raise typer.Exit(1)

    done_line, todo_text, closed_at = mark_todo_done_line(target)
    lines[line - 1] = done_line
    path.write_text("\n".join(lines) + "\n")
    print_success(
        "Done",
        f"{path.relative_to(notebook_dir)}:{line}",
        f"[x] {todo_text}  CLOSED: [{closed_at}]",
    )


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
        console.print("[yellow]No open todos found.[/yellow]")
        raise typer.Exit(0)

    # Group by file
    groups: dict[str, list[TodoItem]] = {}
    for todo in todos:
        groups.setdefault(todo.file, []).append(todo)

    render_summary_table(groups, notebook_dir)


if __name__ == "__main__":
    app()
