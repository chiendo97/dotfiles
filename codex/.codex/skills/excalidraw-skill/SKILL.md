---
name: excalidraw-skill
description: Curl-only REST workflow for creating, editing, inspecting, importing, exporting, and refining diagrams on a local mcp_excalidraw canvas server. Use when Codex needs to control an Excalidraw canvas without MCP tools, using curl against EXPRESS_SERVER_URL or http://127.0.0.1:3000. Covers health checks, element CRUD, batch creation, Mermaid conversion, viewport/image requests, snapshots, and JSON import/export. Requires a running canvas server.
---

# Excalidraw Curl Skill

Use the local canvas REST API with `curl`. Do not use MCP tools or Node helper scripts for this skill.

## Base URL

Use this variable in shell commands:

```bash
EXCALIDRAW_URL="${EXPRESS_SERVER_URL:-http://127.0.0.1:3000}"
```

Start every task by checking the canvas:

```bash
curl -fsS "$EXCALIDRAW_URL/health"
```

If this fails, tell the user to start the canvas:

```bash
cd /path/to/mcp_excalidraw
PORT=3000 npm run canvas
```

## Core Workflow

1. Check health with `GET /health`.
2. Inspect existing state with `GET /api/elements` unless the user asked for a fresh canvas.
3. Plan coordinates before writing JSON. The origin is top-left; x increases right, y increases down.
4. Create shapes in batches with `POST /api/elements/batch`.
5. Query the created elements and verify IDs, positions, and labels.
6. Fix issues with `PUT /api/elements/:id` or `DELETE /api/elements/:id`.
7. Request viewport or image export only when the browser canvas is open.
8. Export useful final state with `GET /api/elements` or `POST /api/export/image`.

For endpoint details and copyable commands, read `references/curl-api.md`.

## REST Payload Rules

- Batch create body must be `{ "elements": [...] }`.
- Use stable custom IDs for every shape that will be referenced later.
- Shape labels use `"label": {"text": "..."}`.
- Arrow bindings use `"start": {"id": "source-id"}` and `"end": {"id": "target-id"}`.
- Do not use MCP-only fields such as `startElementId` or `endElementId`.
- Set `fontFamily` as a string such as `"1"`, or omit it.
- Prefer `--data-binary @payload.json` for diagrams larger than a few elements.
- Use `curl -fsS` so HTTP and connection failures stop the command.

## Minimal Batch Create

```bash
cat > diagram.payload.json <<'JSON'
{
  "elements": [
    {
      "id": "auth-service",
      "type": "rectangle",
      "x": 100,
      "y": 120,
      "width": 180,
      "height": 70,
      "backgroundColor": "#dbeafe",
      "label": { "text": "Auth Service" }
    },
    {
      "id": "user-db",
      "type": "rectangle",
      "x": 420,
      "y": 120,
      "width": 180,
      "height": 70,
      "backgroundColor": "#dcfce7",
      "label": { "text": "User DB" }
    },
    {
      "id": "auth-to-db",
      "type": "arrow",
      "x": 0,
      "y": 0,
      "start": { "id": "auth-service" },
      "end": { "id": "user-db" },
      "label": { "text": "queries" }
    }
  ]
}
JSON

curl -fsS -X POST "$EXCALIDRAW_URL/api/elements/batch" \
  -H "Content-Type: application/json" \
  --data-binary @diagram.payload.json
```

## Layout Rules

- Keep at least 40 px between neighboring shapes.
- Use 60 px height for single-line labels and 80 px for two-line labels.
- Set width to at least `max(160, label_length * 9)`.
- Use free-standing text for background zone labels. Do not put `label.text` on large zone rectangles, because bound text is centered and can overlap children.
- Use arrow labels sparingly. Keep labels short and avoid them on crowded diagrams.
- If an arrow would cross unrelated shapes, use explicit `points` and `elbowed: true` or a curved route with `roundness`.

## Inspect And Fix

List all elements:

```bash
curl -fsS "$EXCALIDRAW_URL/api/elements"
```

Get one element:

```bash
curl -fsS "$EXCALIDRAW_URL/api/elements/auth-service"
```

Update one element:

```bash
curl -fsS -X PUT "$EXCALIDRAW_URL/api/elements/auth-service" \
  -H "Content-Type: application/json" \
  -d '{"id":"auth-service","x":120,"y":140,"label":{"text":"Auth API"}}'
```

Delete one element:

```bash
curl -fsS -X DELETE "$EXCALIDRAW_URL/api/elements/auth-to-db"
```

## Visual Verification

If the browser canvas is open, request zoom-to-content:

```bash
curl -fsS -X POST "$EXCALIDRAW_URL/api/viewport" \
  -H "Content-Type: application/json" \
  -d '{"scrollToContent":true}'
```

Export a PNG result:

```bash
curl -fsS -X POST "$EXCALIDRAW_URL/api/export/image" \
  -H "Content-Type: application/json" \
  -d '{"format":"png","background":true}'
```

The image endpoint returns base64/data URL content. If it returns `503`, open `http://127.0.0.1:3000` in a browser and retry.

## Import, Export, And Snapshots

Export elements:

```bash
curl -fsS "$EXCALIDRAW_URL/api/elements" > diagram.elements.json
```

Overwrite the canvas from an elements file:

```bash
curl -fsS -X POST "$EXCALIDRAW_URL/api/elements/sync" \
  -H "Content-Type: application/json" \
  --data-binary @diagram.elements.json
```

Save a snapshot before risky edits:

```bash
curl -fsS -X POST "$EXCALIDRAW_URL/api/snapshots" \
  -H "Content-Type: application/json" \
  -d '{"name":"before-refactor"}'
```

Restore manually by fetching the snapshot and syncing its `snapshot.elements` array back to `/api/elements/sync`.

## Mermaid Conversion

Mermaid conversion is browser-assisted. Keep the canvas open, then call:

```bash
curl -fsS -X POST "$EXCALIDRAW_URL/api/elements/from-mermaid" \
  -H "Content-Type: application/json" \
  -d '{"mermaidDiagram":"graph TD\n  A[User] --> B[API]\n  B --> C[(Database)]"}'
```

After conversion, query `GET /api/elements`, request viewport fit, and export an image if visual verification is needed.

## Error Recovery

- Health check fails: start `PORT=3000 npm run canvas`.
- Write returns 400: check JSON shape and REST field names.
- Arrow does not bind: query both endpoint IDs, then resend the arrow with `start.id` and `end.id`.
- Image or viewport returns 503: open the browser canvas first.
- Canvas is cluttered and user wants a fresh start: use `DELETE /api/elements/clear` only after confirming the user is okay with clearing the current in-memory canvas.
