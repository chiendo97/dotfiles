---
name: preview
description: Share local Markdown or HTML files as browser preview URLs through Claude Boy Service, with local previewd as a fallback. Use when asked to preview a document, view a local HTML page in a browser, or upload a file for sharing.
---

# Preview documents

Use the Rust service on the VM first. Keep `previewd.py` and `bm.bundle.js` beside this skill for the local fallback. The VM path needs no local server or API key. The default origin is `http://10.30.0.164:8080`; the user's browser needs LAN/VPN access to that address. Override it with `CLAUDE_BOY_API_URL` or `--server`.

Run the helper relative to this skill directory:

```bash
python3 scripts/upload.py /path/to/report.md
python3 scripts/upload.py /path/to/page.html --name review.html
```

Report the printed URL. The source file is untouched. Uploading the same name replaces the hosted document, so choose a descriptive unique name unless replacement is intended. Files persist on the server until explicitly deleted.

Supported extensions: `.md`, `.markdown`, `.html`, `.htm`. Uploads must be UTF-8 and at most 5 MiB each. The service permits 100 MiB of combined source data; delete unused previews if the quota is reached.

Markdown supports tables, task lists, fenced code, heading links, and Mermaid. Theme controls support auto/light/dark. HTML is served without rewriting, with browser sandbox restrictions: scripts can render the page, but cannot use same-origin storage, fetch API data, submit forms, or embed frames. Documents requiring those capabilities need adjustment. Code highlighting and Mermaid's fallback renderer require access to their CDNs.

For connection refusal, timeout, network failure, or HTTP 5xx, use the local fallback below and report that the URL is hosted locally. For HTTP 400 or 413, fix the file/name or report the size limit. HTTP 507 means the VM quota is full: report it, then use local fallback for the requested preview. A timed-out PUT may have completed remotely; fallback does not require deleting that remote copy. Delete a remote document only when requested:

```bash
curl --fail-with-body -X DELETE http://10.30.0.164:8080/v1/previews/report.md
```

The service does not upload referenced local images or stylesheets. Use embedded assets, remote URLs, or separately uploaded HTML/Markdown links that exist on the server.

## Local fallback

Use this path when the VM is unavailable or the user explicitly requests local hosting. It preserves the original Python Markdown renderer and unrestricted local HTML behavior. It requires `uv`; if that dependency is unavailable, report the blocker rather than installing it automatically.

Probe the recorded port before reusing a server. A stale PID file alone is not evidence of a live previewd process; leave unrelated processes alone. If the probe fails, launch previewd and wait for a healthy port:

```bash
PVD="$HOME/.agents/skills/preview/previewd.py"
P=$(cut -d: -f2 "$HOME/.previewd/addr" 2>/dev/null)
if [ -z "$P" ] || ! curl --fail --silent --output /dev/null --max-time 2 "http://127.0.0.1:$P/"; then
  mkdir -p "$HOME/.previewd"
  nohup uv run "$PVD" serve > "$HOME/.previewd/serve.log" 2>&1 &
  for attempt in $(seq 1 30); do
    P=$(cut -d: -f2 "$HOME/.previewd/addr" 2>/dev/null)
    if [ -n "$P" ] && curl --fail --silent --output /dev/null --max-time 2 "http://127.0.0.1:$P/"; then
      break
    fi
    sleep 1
  done
fi
curl --fail --silent --output /dev/null --max-time 2 "http://127.0.0.1:$P/"
```

Proceed with upload only if the final probe succeeds. Otherwise inspect `~/.previewd/serve.log` and report the failure.

```bash
uv run "$PVD" upload /path/to/report.md --server "127.0.0.1:$P"
# Optional URL filename:
uv run "$PVD" upload /path/to/page.html --name review.html --server "127.0.0.1:$P"
```

Local files are copied to `~/.previewd/files/`; a repeated name replaces that local copy. Return the printed URL and identify it as local. For another device, use the workstation's reachable LAN IP in `--server` and explain that the workstation must stay running. A local URL is not a VM-hosted shared URL.
