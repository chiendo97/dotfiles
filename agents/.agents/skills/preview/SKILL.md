---
name: preview
description: >
  Share a local file for browser preview via the previewd service. Use this
  skill whenever the user wants to preview, view in a browser, or share a
  URL for a markdown (.md) or HTML (.html) file, or says "preview this",
  "show me this doc in the browser", or "upload for preview".
---

# preview — serve md/html for browser preview

`previewd.py` (next to this skill) is a single-file local service, run via
`uv run`, that serves `.md`/`.html` files at `http://host:port/filename`.
Set `PVD="$HOME/.agents/skills/preview/previewd.py"` first.

## Workflow

1. **Ensure the server is running** — probe, don't trust the addr file alone:
   ```bash
   PVD="$HOME/.agents/skills/preview/previewd.py"
   P=$(cut -d: -f2 ~/.previewd/addr 2>/dev/null)
   if [ -z "$P" ] || ! curl -s -o /dev/null --max-time 2 http://127.0.0.1:$P/; then
     kill "$(cat ~/.previewd/pid 2>/dev/null)" 2>/dev/null; sleep 0.5   # clear a stale instance
     mkdir -p ~/.previewd && nohup uv run "$PVD" serve \
       > ~/.previewd/serve.log 2>&1 &
     sleep 1
   fi
   cat ~/.previewd/addr
   ```
   Covers all three states: no file, stale file (port refused), and healthy
   (skip restart, keep the current port).

2. **Upload the file.** Prints the preview URL:
   ```bash
   uv run "$PVD" upload /path/to/file.md
   # rename it in the URL:
   uv run "$PVD" upload file.md --name report.md
   ```

3. **Report the URL** (`http://0.0.0.0:PORT/name`) to the user. On the same
   machine `127.0.0.1:PORT` also works; from another machine use its IP.

## Notes

- `.md` is rendered to styled HTML; `.html` is served as-is.
- Files are copied to `~/.previewd/files/` — the source file is untouched.
- Overwriting a name replaces the served copy.
- URLs default to the recorded `0.0.0.0`; pass `upload --server HOST:PORT`
  to print a specific host (e.g. the machine's LAN IP or `127.0.0.1`).
- If a request to a printed URL fails (stale addr), re-run step 1 — it
  restarts on a fresh port and re-upload prints the new URL.