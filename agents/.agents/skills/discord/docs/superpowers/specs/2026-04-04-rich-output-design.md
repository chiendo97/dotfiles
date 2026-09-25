# Rich Output for discord_cli.py

## Goal

Replace raw `print()` output with Rich library renderables for better terminal readability. Tables for listings, Panels for messages, styled Text elsewhere. Errors stay as plain stderr.

## Dependencies

Add `rich` to PEP 723 inline metadata.

Module-level: `console = Console()` — all non-error output goes through this.

## Model `.display()` Changes

Return type changes from `str` to `RenderableType` for all models.

### Message

`Panel` containing content lines, embed renderables, and attachment renderables.
- Title: `[bold]{username}[/bold] [dim]{timestamp}[/dim]`
- Subtitle: `msg:{id}`

### Embed

`Text` with styled title (`[italic]`), dim URL, indented description and fields.

### Attachment

`Text`: `[dim]📎 {filename}[/dim]` with URL.

### Channel

`Text`: `[bold]#{name}[/bold] [dim](id:{id}, type:{type})[/dim]`

### ActiveThread

`Text`: `[bold]💬 {name}[/bold]` with dim metadata line (msgs, members, created).

### Thread

Styled confirmation text.

### SentMessage

Each display method (`display_sent`, `display_edited`, `display_file_sent`) returns styled `Text` — bold confirmation line, dim content.

## Command-Level Changes

### `channels`

`Table` with columns: Name, ID, Type. Category groups rendered as `Rule` headers or bold text above each group.

### `threads`

`Table` with columns: Name, ID, Parent, Messages, Members, Created. Grouped by parent channel with headers.

### `get`

Iterates messages, calls `console.print(msg.display())` for each (renders as Panel).

### `send`, `edit`, `send-file`, `thread`, `rename`, `react`

Call `console.print(model.display())` directly — no table needed.

### Summary lines

Footer lines like `--- 5 message(s) ---` become `console.print(f"[dim]--- {count} ...[/dim]")`.

## Unchanged

- Error output stays as `print(..., file=sys.stderr)` — no Rich styling.
- All API logic, models, enums, type annotations unchanged.
- `resolve_channel_id`, `api_request`, `build_multipart` unchanged.
