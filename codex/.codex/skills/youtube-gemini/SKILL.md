---
name: youtube-gemini
description: "Summarize and analyze public YouTube videos with Gemini's native video understanding, including audio, visuals, timestamps, key points, and verification caveats. Use when a user supplies a YouTube URL and asks for a summary, explanation, content analysis, chronology, takeaways, or questions about the video."
---

# YouTube Gemini

Use the bundled CLI so Gemini receives the public YouTube URL as native video input instead of relying on captions or transcript scraping.

## Run

```bash
uv run "${CODEX_HOME:-$HOME/.codex}/skills/youtube-gemini/scripts/youtube_gemini.py" '<youtube-url>'
```

The CLI reads `GEMINI_API_KEY` or `GOOGLE_API_KEY`. If neither is set, it checks `~/.secrets/gemini-api-key` and `~/.gemini_token`. Never print or pass the key as a command-line argument.

Use a custom request when the user wants something other than the standard summary:

```bash
uv run "${CODEX_HOME:-$HOME/.codex}/skills/youtube-gemini/scripts/youtube_gemini.py" \
  '<youtube-url>' \
  --prompt 'Explain the implementation choices and list security concerns with timestamps.'
```

Use `--output <path>` when the user asks to save the result, and `--json` only when structured API output is needed for downstream processing. The default model is `gemini-3.6-flash`; override it with `--model` only when requested or when the API reports that the model is unavailable.

## Reporting

- Treat the output as Gemini's analysis, not independently verified fact.
- Preserve timestamps when present.
- State clearly when the video is private, unlisted, unavailable, or rejected by the API.
- For factual research or high-stakes claims, verify important claims against primary sources before presenting them as confirmed.
