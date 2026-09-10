#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


DEFAULT_MODEL = "gemini-3.6-flash"
API_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
DEFAULT_PROMPT = """Analyze the full video using both its spoken audio and visible content.

Provide:
1. A concise overall summary.
2. The main points in chronological order with approximate timestamps.
3. The key conclusion or practical takeaway.
4. Claims that may need independent verification.

Do not invent details. Explicitly note anything unclear."""
KEY_FILES = (Path("~/.secrets/gemini-api-key"), Path("~/.gemini_token"))
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize a public YouTube video with Gemini native video understanding."
    )
    parser.add_argument("url", help="Public YouTube video URL")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Gemini model name")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="Analysis request")
    parser.add_argument("--output", type=Path, help="Write output to this file")
    parser.add_argument(
        "--json", action="store_true", help="Print the complete API response as JSON"
    )
    return parser.parse_args()


def validate_youtube_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in YOUTUBE_HOSTS:
        raise ValueError("Expected a youtube.com or youtu.be URL")
    return value


def read_api_key() -> str:
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if value := os.getenv(name):
            return value.strip()

    for candidate in KEY_FILES:
        path = candidate.expanduser()
        if path.is_file() and (value := path.read_text(encoding="utf-8").strip()):
            return value

    raise RuntimeError(
        "Gemini API key not found. Set GEMINI_API_KEY or create ~/.gemini_token."
    )


def call_gemini(
    *, api_key: str, model: str, prompt: str, video_url: str
) -> dict[str, Any]:
    payload = {
        "model": model,
        "input": [
            {"type": "text", "text": prompt},
            {"type": "video", "uri": video_url},
        ],
    }
    request = Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )

    try:
        with urlopen(request, timeout=300) as response:
            return json.load(response)
    except HTTPError as error:
        try:
            body = json.loads(error.read().decode("utf-8"))
            detail = body.get("error", {}).get("message", str(error))
        except (UnicodeDecodeError, json.JSONDecodeError):
            detail = str(error)
        raise RuntimeError(
            f"Gemini API returned HTTP {error.code}: {detail}"
        ) from error
    except URLError as error:
        raise RuntimeError(f"Could not reach the Gemini API: {error.reason}") from error


def extract_text(response: dict[str, Any]) -> str:
    texts: list[str] = []
    for step in response.get("steps", []):
        for content in step.get("content", []):
            if content.get("type") == "text" and content.get("text"):
                texts.append(content["text"])

    if not texts and response.get("output_text"):
        texts.append(response["output_text"])
    if not texts:
        raise RuntimeError("Gemini returned no text output")
    return "\n".join(texts).strip()


def main() -> int:
    args = parse_args()
    try:
        video_url = validate_youtube_url(args.url)
        response = call_gemini(
            api_key=read_api_key(),
            model=args.model,
            prompt=args.prompt,
            video_url=video_url,
        )
        result = (
            json.dumps(response, ensure_ascii=False, indent=2)
            if args.json
            else extract_text(response)
        )
        if args.output:
            args.output.expanduser().write_text(f"{result}\n", encoding="utf-8")
        else:
            print(result)
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"youtube-gemini: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
