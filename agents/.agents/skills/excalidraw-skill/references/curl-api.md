# Excalidraw Curl API

## Defaults

```bash
EXCALIDRAW_URL="${EXPRESS_SERVER_URL:-http://127.0.0.1:3000}"
```

Use `curl -fsS` for every request. Add `| jq .` when readable JSON helps.

## System

Health:

```bash
curl -fsS "$EXCALIDRAW_URL/health"
```

Sync status:

```bash
curl -fsS "$EXCALIDRAW_URL/api/sync/status"
```

## Elements

List all elements:

```bash
curl -fsS "$EXCALIDRAW_URL/api/elements"
```

Get one element:

```bash
curl -fsS "$EXCALIDRAW_URL/api/elements/<id>"
```

Create one element:

```bash
curl -fsS -X POST "$EXCALIDRAW_URL/api/elements" \
  -H "Content-Type: application/json" \
  -d '{"id":"box-1","type":"rectangle","x":100,"y":100,"width":180,"height":70,"label":{"text":"Box 1"}}'
```

Batch create:

```bash
curl -fsS -X POST "$EXCALIDRAW_URL/api/elements/batch" \
  -H "Content-Type: application/json" \
  --data-binary @payload.json
```

Expected `payload.json`:

```json
{
  "elements": [
    {
      "id": "source",
      "type": "rectangle",
      "x": 100,
      "y": 100,
      "width": 180,
      "height": 70,
      "label": { "text": "Source" }
    },
    {
      "id": "target",
      "type": "rectangle",
      "x": 420,
      "y": 100,
      "width": 180,
      "height": 70,
      "label": { "text": "Target" }
    },
    {
      "id": "source-target",
      "type": "arrow",
      "x": 0,
      "y": 0,
      "start": { "id": "source" },
      "end": { "id": "target" },
      "label": { "text": "calls" }
    }
  ]
}
```

Update:

```bash
curl -fsS -X PUT "$EXCALIDRAW_URL/api/elements/<id>" \
  -H "Content-Type: application/json" \
  -d '{"id":"<id>","x":140,"y":120,"label":{"text":"New Label"}}'
```

Delete:

```bash
curl -fsS -X DELETE "$EXCALIDRAW_URL/api/elements/<id>"
```

Clear:

```bash
curl -fsS -X DELETE "$EXCALIDRAW_URL/api/elements/clear"
```

Search by type:

```bash
curl -fsS "$EXCALIDRAW_URL/api/elements/search?type=rectangle"
```

## Payload Notes

Supported element types include `rectangle`, `ellipse`, `diamond`, `arrow`, `text`, `freedraw`, `line`, and `image`.

Common shape fields:

```json
{
  "id": "stable-id",
  "type": "rectangle",
  "x": 100,
  "y": 100,
  "width": 180,
  "height": 70,
  "backgroundColor": "#dbeafe",
  "strokeColor": "#1e3a8a",
  "strokeWidth": 2,
  "fillStyle": "solid",
  "label": { "text": "Label" }
}
```

Standalone text:

```json
{
  "id": "title",
  "type": "text",
  "x": 100,
  "y": 40,
  "width": 300,
  "height": 40,
  "text": "System Overview",
  "fontSize": 24
}
```

Arrow binding:

```json
{
  "id": "a-b",
  "type": "arrow",
  "x": 0,
  "y": 0,
  "start": { "id": "a" },
  "end": { "id": "b" },
  "endArrowhead": "arrow"
}
```

Elbowed arrow:

```json
{
  "id": "routed",
  "type": "arrow",
  "x": 100,
  "y": 100,
  "points": [[0, 0], [0, -50], [220, -50], [220, 0]],
  "elbowed": true,
  "endArrowhead": "arrow"
}
```

## Import And Export

Export the server element payload:

```bash
curl -fsS "$EXCALIDRAW_URL/api/elements" > diagram.elements.json
```

Append elements from a file:

```bash
curl -fsS -X POST "$EXCALIDRAW_URL/api/elements/batch" \
  -H "Content-Type: application/json" \
  --data-binary @payload.json
```

Overwrite from a server export shape:

```bash
curl -fsS -X POST "$EXCALIDRAW_URL/api/elements/sync" \
  -H "Content-Type: application/json" \
  --data-binary @diagram.elements.json
```

`/api/elements/sync` expects a body with an `elements` array. A response from `GET /api/elements` already has this shape.

## Mermaid

```bash
curl -fsS -X POST "$EXCALIDRAW_URL/api/elements/from-mermaid" \
  -H "Content-Type: application/json" \
  -d '{"mermaidDiagram":"graph TD\n  A[User] --> B[API]\n  B --> C[(Database)]"}'
```

This broadcasts the conversion request to the browser canvas. Keep `http://127.0.0.1:3000` open.

## Image Export And Viewport

Fit viewport to content:

```bash
curl -fsS -X POST "$EXCALIDRAW_URL/api/viewport" \
  -H "Content-Type: application/json" \
  -d '{"scrollToContent":true}'
```

Export PNG:

```bash
curl -fsS -X POST "$EXCALIDRAW_URL/api/export/image" \
  -H "Content-Type: application/json" \
  -d '{"format":"png","background":true}'
```

Export SVG:

```bash
curl -fsS -X POST "$EXCALIDRAW_URL/api/export/image" \
  -H "Content-Type: application/json" \
  -d '{"format":"svg","background":true}'
```

These endpoints require at least one browser client connected.

## Snapshots

Save:

```bash
curl -fsS -X POST "$EXCALIDRAW_URL/api/snapshots" \
  -H "Content-Type: application/json" \
  -d '{"name":"before-change"}'
```

List:

```bash
curl -fsS "$EXCALIDRAW_URL/api/snapshots"
```

Fetch:

```bash
curl -fsS "$EXCALIDRAW_URL/api/snapshots/before-change"
```

To restore a snapshot, send `{"elements": <snapshot.elements>}` to `/api/elements/sync`.
