Always use `uv` to manage and run Python — never use system Python directly.

- Use `uv run` to execute Python scripts (e.g., `uv run python script.py`)
- Use `uv add` / `uv remove` to manage dependencies (never use `pip` or `uv pip`)
- Use `uv venv` to create virtual environments
- Never invoke `python`, `python3`, or `pip` directly — always go through `uv`
