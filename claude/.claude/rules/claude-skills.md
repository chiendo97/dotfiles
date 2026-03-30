# Claude Skill CLI Development Rules

When building or modifying CLI tools that power Claude skills (e.g. `notion_cli.py`, `github_cli.py`):

## Stack

- **CLI framework**: typer with `Annotated[..., typer.Option()]` style
- **Data models**: pydantic `BaseModel` for config parsing and domain objects
- **Type-checking**: basedpyright must pass clean
- **Runner**: single-file scripts with PEP 723 inline metadata, run via `uv run`

## Type Safety

- All functions must have full type annotations.
- `dict[str, Any]` is acceptable only at external API boundaries (JSON responses). Everywhere else, use typed models.
- Suppress only `reportExplicitAny` and `reportAny` in pyrightconfig — these cascade from untyped API responses and are unfixable without modeling the entire external API schema. All other strict checks stay enabled.
- Prefer inline `# pyright: ignore[rule]` over broad pyrightconfig suppressions when only one or two lines need it.

## Enums for Writes, Strings for Reads

Use `str, Enum` for command parameters that **set** values (create, update). Use plain `str` for parameters that **filter/query** — external systems often have custom values not in the enum.

## Typer Patterns

- `typer.Option(parser=...)` for custom type parsing (e.g. `date.fromisoformat`). Define shared `Annotated` type aliases for options reused across commands.
- Module-level typed variables set in `@app.callback()` for shared state — not a `dict[str, Any]` state bag.
- Validate environment variables (tokens, keys) once in the callback, cache the value.

## Pydantic Patterns

- `ConfigDict(extra="ignore")` on config models so YAML/JSON configs can contain fields the CLI doesn't use.
- `Model.from_response()` classmethods to encapsulate external API response parsing.
- `Model.display()` methods as the single source of truth for terminal formatting — never inline display logic in commands.

## API Boundary Discipline

- Always shallow-copy mutable dicts before paginating or modifying them.
- Know and respect API limits (e.g. Notion's 2000-char rich_text limit) — handle them in helper functions, not callers.
- Use API-level filtering over client-side full-table scans when the API supports it.
- When aggregating results from multiple sources (e.g. multi-project queries), re-sort the combined results.
