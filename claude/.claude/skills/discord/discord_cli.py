#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["certifi"]
# ///
"""Discord CLI — interact with Discord channels, threads, and DMs via REST API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import ssl
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import certifi

SSL_CTX = ssl.create_default_context(cafile=certifi.where())

BASE_URL = "https://discord.com/api/v10"

CHANNEL_TYPES = {
    0: "text",
    1: "dm",
    2: "voice",
    4: "category",
    5: "announcement",
    10: "announcement_thread",
    11: "public_thread",
    12: "private_thread",
    13: "stage",
    14: "directory",
    15: "forum",
    16: "media",
}


def get_token() -> str:
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    return token


def get_guild_id(override: str | None = None) -> str:
    guild_id = override or os.environ.get("DISCORD_GUILD_ID")
    if not guild_id:
        print("Error: DISCORD_GUILD_ID environment variable is not set and --guild-id not provided.", file=sys.stderr)
        sys.exit(1)
    return guild_id


def api_request(
    method: str,
    path: str,
    *,
    body: dict | None = None,
    content_type: str = "application/json",
    raw_body: bytes | None = None,
    extra_headers: dict[str, str] | None = None,
) -> dict | list | None:
    """Make an authenticated request to the Discord API."""
    token = get_token()
    url = f"{BASE_URL}{path}"

    headers = {
        "Authorization": f"Bot {token}",
        "User-Agent": "DiscordCLI/1.0",
    }

    if extra_headers:
        headers.update(extra_headers)

    data = None
    if raw_body is not None:
        data = raw_body
    elif body is not None:
        headers["Content-Type"] = content_type
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as resp:
            resp_body = resp.read()
            if resp_body:
                return json.loads(resp_body)
            return None
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        try:
            error_json = json.loads(error_body)
            print(f"Error {e.code}: {error_json.get('message', error_body)}", file=sys.stderr)
        except json.JSONDecodeError:
            print(f"Error {e.code}: {error_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def resolve_channel_id(
    *,
    channel_id: str | None = None,
    thread_id: str | None = None,
    user_id: str | None = None,
) -> str:
    """Resolve the target channel ID from the various ID options."""
    if channel_id:
        return channel_id
    if thread_id:
        return thread_id
    if user_id:
        # Create or get DM channel
        result = api_request("POST", "/users/@me/channels", body={"recipient_id": user_id})
        if result and "id" in result:
            return result["id"]
        print("Error: failed to create DM channel.", file=sys.stderr)
        sys.exit(1)
    print("Error: one of --channel-id, --thread-id, or --user-id is required.", file=sys.stderr)
    sys.exit(1)


def build_multipart(fields: dict[str, str], file_path: str, file_field: str = "files[0]") -> tuple[bytes, str]:
    """Build multipart/form-data body for file upload."""
    boundary = "----DiscordCLIBoundary9876543210"
    lines: list[bytes] = []

    for key, value in fields.items():
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        lines.append(f"{value}\r\n".encode())

    # File part
    filename = Path(file_path).name
    lines.append(f"--{boundary}\r\n".encode())
    lines.append(f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode())
    lines.append(b"Content-Type: application/octet-stream\r\n\r\n")
    with open(file_path, "rb") as f:
        lines.append(f.read())
    lines.append(b"\r\n")
    lines.append(f"--{boundary}--\r\n".encode())

    body = b"".join(lines)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def format_message(msg: dict) -> str:
    """Format a single message for display."""
    author = msg.get("author", {})
    username = author.get("username", "unknown")
    msg_id = msg.get("id", "?")
    content = msg.get("content", "")
    timestamp = msg.get("timestamp", "")[:19].replace("T", " ")
    attachments = msg.get("attachments", [])

    lines = [f"[{timestamp}] {username} (msg:{msg_id})"]
    if content:
        lines.append(f"  {content}")
    for att in attachments:
        lines.append(f"  [file: {att.get('filename', '?')} — {att.get('url', '')}]")
    return "\n".join(lines)


# --- Subcommand handlers ---


def cmd_send(args: argparse.Namespace) -> None:
    """Send a message to a channel, thread, or DM."""
    target = resolve_channel_id(
        channel_id=args.channel_id,
        thread_id=args.thread_id,
        user_id=args.user_id,
    )

    body: dict = {"content": args.message}
    if args.reply_to:
        body["message_reference"] = {"message_id": args.reply_to}

    result = api_request("POST", f"/channels/{target}/messages", body=body)
    if result:
        print(f"Sent (msg:{result['id']}) to channel:{target}")
        if result.get("content"):
            print(f"  {result['content']}")


def cmd_edit(args: argparse.Namespace) -> None:
    """Edit an existing message."""
    result = api_request(
        "PATCH",
        f"/channels/{args.channel_id}/messages/{args.message_id}",
        body={"content": args.content},
    )
    if result:
        print(f"Edited (msg:{result['id']}) in channel:{args.channel_id}")
        if result.get("content"):
            print(f"  {result['content']}")


def cmd_get(args: argparse.Namespace) -> None:
    """Get recent messages from a channel."""
    params = urllib.parse.urlencode({"limit": args.limit})
    result = api_request("GET", f"/channels/{args.channel_id}/messages?{params}")
    if result and isinstance(result, list):
        # Messages come newest-first; reverse for chronological display
        for msg in reversed(result):
            print(format_message(msg))
            print()
        print(f"--- {len(result)} message(s) ---")
    else:
        print("No messages found.")


def cmd_channels(args: argparse.Namespace) -> None:
    """List guild channels."""
    guild_id = get_guild_id(args.guild_id)
    result = api_request("GET", f"/guilds/{guild_id}/channels")
    if result and isinstance(result, list):
        # Group by category
        categories: dict[str | None, list[dict]] = {}
        cat_names: dict[str, str] = {}
        for ch in result:
            if ch.get("type") == 4:
                cat_names[ch["id"]] = ch.get("name", "?")

        for ch in result:
            if ch.get("type") == 4:
                continue
            parent = ch.get("parent_id")
            categories.setdefault(parent, []).append(ch)

        # Print uncategorized first
        for parent_id in [None, *sorted(cat_names.keys(), key=lambda k: cat_names.get(k, ""))]:
            if parent_id is None:
                header = "[No Category]"
            else:
                header = f"[{cat_names.get(parent_id, parent_id)}]"

            channels = categories.get(parent_id, [])
            if not channels:
                continue

            print(header)
            for ch in sorted(channels, key=lambda c: c.get("position", 0)):
                ch_type = CHANNEL_TYPES.get(ch.get("type", -1), "unknown")
                print(f"  #{ch.get('name', '?')}  (id:{ch['id']}, type:{ch_type})")
            print()

        print(f"--- {len(result)} channel(s) ---")
    else:
        print("No channels found.")


def cmd_thread(args: argparse.Namespace) -> None:
    """Create a thread."""
    if args.message_id:
        # Thread from a message
        result = api_request(
            "POST",
            f"/channels/{args.channel_id}/messages/{args.message_id}/threads",
            body={"name": args.name},
        )
    else:
        # Standalone thread
        result = api_request(
            "POST",
            f"/channels/{args.channel_id}/threads",
            body={
                "name": args.name,
                "type": 11,  # public thread
            },
        )
    if result:
        print(f"Created thread: {result.get('name', '?')} (id:{result['id']})")


def cmd_react(args: argparse.Namespace) -> None:
    """React to a message with an emoji."""
    emoji = urllib.parse.quote(args.emoji, safe="")
    api_request(
        "PUT",
        f"/channels/{args.channel_id}/messages/{args.message_id}/reactions/{emoji}/@me",
    )
    print(f"Reacted with :{args.emoji}: on msg:{args.message_id}")


def cmd_send_file(args: argparse.Namespace) -> None:
    """Send a file to a channel, thread, or DM."""
    target = resolve_channel_id(
        channel_id=args.channel_id,
        thread_id=args.thread_id,
        user_id=args.user_id,
    )

    if not Path(args.file).is_file():
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    fields = {}
    if args.message:
        payload = json.dumps({"content": args.message})
        fields["payload_json"] = payload

    raw_body, content_type = build_multipart(fields, args.file)

    result = api_request(
        "POST",
        f"/channels/{target}/messages",
        raw_body=raw_body,
        extra_headers={"Content-Type": content_type},
    )
    if result:
        attachments = result.get("attachments", [])
        att_info = f", {len(attachments)} attachment(s)" if attachments else ""
        print(f"Sent file (msg:{result['id']}) to channel:{target}{att_info}")
        if result.get("content"):
            print(f"  {result['content']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="discord_cli",
        description="Discord bot CLI — interact with channels, threads, and DMs.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- send ---
    p_send = subparsers.add_parser("send", help="Send a message")
    target_group = p_send.add_mutually_exclusive_group(required=True)
    target_group.add_argument("--channel-id", help="Target channel ID")
    target_group.add_argument("--thread-id", help="Target thread ID")
    target_group.add_argument("--user-id", help="Target user ID (sends DM)")
    p_send.add_argument("--reply-to", help="Message ID to reply to")
    p_send.add_argument("message", help="Message text to send")
    p_send.set_defaults(func=cmd_send)

    # --- edit ---
    p_edit = subparsers.add_parser("edit", help="Edit a message")
    p_edit.add_argument("--channel-id", required=True, help="Channel containing the message")
    p_edit.add_argument("--message-id", required=True, help="Message ID to edit")
    p_edit.add_argument("content", help="New message content")
    p_edit.set_defaults(func=cmd_edit)

    # --- get ---
    p_get = subparsers.add_parser("get", help="Get recent messages")
    p_get.add_argument("--channel-id", required=True, help="Channel to read from")
    p_get.add_argument("--limit", type=int, default=20, help="Number of messages (default: 20)")
    p_get.set_defaults(func=cmd_get)

    # --- channels ---
    p_channels = subparsers.add_parser("channels", help="List guild channels")
    p_channels.add_argument("--guild-id", help="Guild ID (defaults to DISCORD_GUILD_ID env)")
    p_channels.set_defaults(func=cmd_channels)

    # --- thread ---
    p_thread = subparsers.add_parser("thread", help="Create a thread")
    p_thread.add_argument("--channel-id", required=True, help="Parent channel ID")
    p_thread.add_argument("--name", required=True, help="Thread name")
    p_thread.add_argument("--message-id", help="Message ID to create thread from")
    p_thread.set_defaults(func=cmd_thread)

    # --- react ---
    p_react = subparsers.add_parser("react", help="React to a message")
    p_react.add_argument("--channel-id", required=True, help="Channel containing the message")
    p_react.add_argument("--message-id", required=True, help="Message ID to react to")
    p_react.add_argument("--emoji", required=True, help="Emoji name (e.g. thumbsup, fire)")
    p_react.set_defaults(func=cmd_react)

    # --- send-file ---
    p_file = subparsers.add_parser("send-file", help="Send a file")
    file_target = p_file.add_mutually_exclusive_group(required=True)
    file_target.add_argument("--channel-id", help="Target channel ID")
    file_target.add_argument("--thread-id", help="Target thread ID")
    file_target.add_argument("--user-id", help="Target user ID (sends DM)")
    p_file.add_argument("--file", required=True, help="Path to file to send")
    p_file.add_argument("--message", help="Optional message text with the file")
    p_file.set_defaults(func=cmd_send_file)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
