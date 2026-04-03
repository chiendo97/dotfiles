#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["certifi", "typer", "pydantic"]
# ///
"""Discord CLI — interact with Discord channels, threads, and DMs via REST API."""

from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

import certifi
import typer
from pydantic import BaseModel, ConfigDict

SSL_CTX = ssl.create_default_context(cafile=certifi.where())

BASE_URL = "https://discord.com/api/v10"

CHANNEL_TYPES: dict[int, str] = {
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


# ---------------------------------------------------------------------------
# Enums for write parameters
# ---------------------------------------------------------------------------


class ThreadType(int, Enum):
    """Thread type for thread creation."""

    PUBLIC = 11
    PRIVATE = 12
    ANNOUNCEMENT = 10


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class Attachment(BaseModel):
    """A file attachment on a Discord message."""

    model_config = ConfigDict(extra="ignore")  # pyright: ignore[reportUnannotatedClassAttribute]

    id: str
    filename: str = "?"
    url: str = ""

    def display(self) -> str:
        return f"  [file: {self.filename} — {self.url}]"


class Author(BaseModel):
    """A Discord message author."""

    model_config = ConfigDict(extra="ignore")  # pyright: ignore[reportUnannotatedClassAttribute]

    id: str = "0"
    username: str = "unknown"


class EmbedField(BaseModel):
    """A field within a Discord embed."""

    model_config = ConfigDict(extra="ignore")  # pyright: ignore[reportUnannotatedClassAttribute]

    name: str = ""
    value: str = ""
    inline: bool = False


class Embed(BaseModel):
    """A Discord message embed."""

    model_config = ConfigDict(extra="ignore")  # pyright: ignore[reportUnannotatedClassAttribute]

    title: str = ""
    description: str = ""
    url: str = ""
    color: int | None = None
    fields: list[EmbedField] = []

    def display(self) -> str:
        lines: list[str] = []
        if self.title:
            header = f"  [embed] {self.title}"
            if self.url:
                header += f" — {self.url}"
            lines.append(header)
        elif self.url:
            lines.append(f"  [embed] {self.url}")
        if self.description:
            for desc_line in self.description.split("\n"):
                lines.append(f"    {desc_line}")
        for field in self.fields:
            lines.append(f"    {field.name}: {field.value}")
        return "\n".join(lines)


class Message(BaseModel):
    """A Discord message."""

    model_config = ConfigDict(extra="ignore")  # pyright: ignore[reportUnannotatedClassAttribute]

    id: str
    content: str = ""
    timestamp: str = ""
    author: Author = Author()
    attachments: list[Attachment] = []
    embeds: list[Embed] = []

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> Message:
        return cls.model_validate(data)

    def display(self) -> str:
        ts = self.timestamp[:19].replace("T", " ")
        lines = [f"[{ts}] {self.author.username} (msg:{self.id})"]
        if self.content:
            lines.append(f"  {self.content}")
        for embed in self.embeds:
            lines.append(embed.display())
        for att in self.attachments:
            lines.append(att.display())
        return "\n".join(lines)


class Channel(BaseModel):
    """A Discord guild channel."""

    model_config = ConfigDict(extra="ignore")  # pyright: ignore[reportUnannotatedClassAttribute]

    id: str
    name: str = "?"
    type: int = 0
    position: int = 0
    parent_id: str | None = None

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> Channel:
        return cls.model_validate(data)

    @property
    def type_name(self) -> str:
        return CHANNEL_TYPES.get(self.type, "unknown")

    def display(self) -> str:
        return f"  #{self.name}  (id:{self.id}, type:{self.type_name})"


class ThreadMetadata(BaseModel):
    """Discord thread metadata."""

    model_config = ConfigDict(extra="ignore")  # pyright: ignore[reportUnannotatedClassAttribute]

    archived: bool = False
    create_timestamp: str | None = None


class Thread(BaseModel):
    """A created Discord thread."""

    model_config = ConfigDict(extra="ignore")  # pyright: ignore[reportUnannotatedClassAttribute]

    id: str
    name: str = "?"

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> Thread:
        return cls.model_validate(data)

    def display(self) -> str:
        return f"Created thread: {self.name} (id:{self.id})"


class ActiveThread(BaseModel):
    """An active Discord thread with metadata."""

    model_config = ConfigDict(extra="ignore")  # pyright: ignore[reportUnannotatedClassAttribute]

    id: str
    name: str = "?"
    parent_id: str | None = None
    message_count: int = 0
    member_count: int = 0
    thread_metadata: ThreadMetadata = ThreadMetadata()

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> ActiveThread:
        return cls.model_validate(data)

    def display(self, parent_name: str | None = None) -> str:
        created = ""
        if self.thread_metadata.create_timestamp:
            created = self.thread_metadata.create_timestamp[:19].replace("T", " ")
        parent_info = f" in #{parent_name}" if parent_name else ""
        return (
            f"  💬 {self.name}  (id:{self.id}){parent_info}\n"
            f"     msgs:{self.message_count} | members:{self.member_count} | created:{created}"
        )


class SentMessage(BaseModel):
    """Result of sending/editing a message."""

    model_config = ConfigDict(extra="ignore")  # pyright: ignore[reportUnannotatedClassAttribute]

    id: str
    content: str = ""
    attachments: list[Attachment] = []

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> SentMessage:
        return cls.model_validate(data)

    def display_sent(self, target: str) -> str:
        lines = [f"Sent (msg:{self.id}) to channel:{target}"]
        if self.content:
            lines.append(f"  {self.content}")
        return "\n".join(lines)

    def display_edited(self, channel_id: str) -> str:
        lines = [f"Edited (msg:{self.id}) in channel:{channel_id}"]
        if self.content:
            lines.append(f"  {self.content}")
        return "\n".join(lines)

    def display_file_sent(self, target: str) -> str:
        att_info = f", {len(self.attachments)} attachment(s)" if self.attachments else ""
        lines = [f"Sent file (msg:{self.id}) to channel:{target}{att_info}"]
        if self.content:
            lines.append(f"  {self.content}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Module-level typed state (set in app.callback)
# ---------------------------------------------------------------------------

_token: str = ""
_guild_id: str = ""

app = typer.Typer(
    name="discord_cli",
    help="Discord bot CLI — interact with channels, threads, and DMs.",
    no_args_is_help=True,
)


@app.callback()
def _callback(  # pyright: ignore[reportUnusedFunction]
    guild_id: Annotated[str, typer.Option("--guild-id", envvar="DISCORD_GUILD_ID", help="Default guild ID")] = "",
) -> None:
    """Validate environment and cache shared state."""
    global _token, _guild_id  # noqa: PLW0603
    token = os.environ.get("DISCORD_TOKEN", "")
    if not token:
        print("Error: DISCORD_TOKEN environment variable is not set.", file=sys.stderr)
        raise typer.Exit(code=1)
    _token = token
    _guild_id = guild_id


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


def api_request(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    content_type: str = "application/json",
    raw_body: bytes | None = None,
    extra_headers: dict[str, str] | None = None,
) -> dict[str, Any] | list[dict[str, Any]] | None:
    """Make an authenticated request to the Discord API."""
    url = f"{BASE_URL}{path}"

    headers: dict[str, str] = {
        "Authorization": f"Bot {_token}",
        "User-Agent": "DiscordCLI/1.0",
    }

    if extra_headers:
        headers = {**headers, **extra_headers}

    data: bytes | None = None
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
            error_json: dict[str, Any] = json.loads(error_body)
            print(f"Error {e.code}: {error_json.get('message', error_body)}", file=sys.stderr)
        except json.JSONDecodeError:
            print(f"Error {e.code}: {error_body}", file=sys.stderr)
        raise typer.Exit(code=1) from None
    except urllib.error.URLError as e:
        print(f"Network error: {e.reason}", file=sys.stderr)
        raise typer.Exit(code=1) from None


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
        result = api_request("POST", "/users/@me/channels", body={"recipient_id": user_id})
        if result and isinstance(result, dict) and "id" in result:
            return str(result["id"])
        print("Error: failed to create DM channel.", file=sys.stderr)
        raise typer.Exit(code=1)
    print("Error: one of --channel-id, --thread-id, or --user-id is required.", file=sys.stderr)
    raise typer.Exit(code=1)


def build_multipart(fields: dict[str, str], file_path: str, file_field: str = "files[0]") -> tuple[bytes, str]:
    """Build multipart/form-data body for file upload."""
    boundary = "----DiscordCLIBoundary9876543210"
    lines: list[bytes] = []

    for key, value in fields.items():
        lines.append(f"--{boundary}\r\n".encode())
        lines.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        lines.append(f"{value}\r\n".encode())

    filename = Path(file_path).name
    lines.append(f"--{boundary}\r\n".encode())
    lines.append(f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'.encode())
    lines.append(b"Content-Type: application/octet-stream\r\n\r\n")
    with open(file_path, "rb") as f:
        lines.append(f.read())
    lines.append(b"\r\n")
    lines.append(f"--{boundary}--\r\n".encode())

    body = b"".join(lines)
    ct = f"multipart/form-data; boundary={boundary}"
    return body, ct


# ---------------------------------------------------------------------------
# Shared option aliases
# ---------------------------------------------------------------------------

ChannelIdOpt = Annotated[str | None, typer.Option("--channel-id", help="Target channel ID")]
ThreadIdOpt = Annotated[str | None, typer.Option("--thread-id", help="Target thread ID")]
UserIdOpt = Annotated[str | None, typer.Option("--user-id", help="Target user ID (sends DM)")]


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def send(
    message: Annotated[str, typer.Argument(help="Message text to send")],
    channel_id: ChannelIdOpt = None,
    thread_id: ThreadIdOpt = None,
    user_id: UserIdOpt = None,
    reply_to: Annotated[str | None, typer.Option("--reply-to", help="Message ID to reply to")] = None,
) -> None:
    """Send a message to a channel, thread, or DM."""
    target = resolve_channel_id(channel_id=channel_id, thread_id=thread_id, user_id=user_id)

    body: dict[str, Any] = {"content": message}
    if reply_to:
        body["message_reference"] = {"message_id": reply_to}

    result = api_request("POST", f"/channels/{target}/messages", body=body)
    if result and isinstance(result, dict):
        msg = SentMessage.from_response(result)
        print(msg.display_sent(target))


@app.command()
def edit(
    channel_id: Annotated[str, typer.Option("--channel-id", help="Channel containing the message")],
    message_id: Annotated[str, typer.Option("--message-id", help="Message ID to edit")],
    content: Annotated[str, typer.Argument(help="New message content")],
) -> None:
    """Edit an existing message."""
    result = api_request(
        "PATCH",
        f"/channels/{channel_id}/messages/{message_id}",
        body={"content": content},
    )
    if result and isinstance(result, dict):
        msg = SentMessage.from_response(result)
        print(msg.display_edited(channel_id))


@app.command()
def get(
    channel_id: Annotated[str, typer.Option("--channel-id", help="Channel to read from")],
    limit: Annotated[int, typer.Option("--limit", help="Number of messages (default: 20, max: 100)")] = 20,
) -> None:
    """Get recent messages from a channel."""
    params = urllib.parse.urlencode({"limit": limit})
    result = api_request("GET", f"/channels/{channel_id}/messages?{params}")
    if result and isinstance(result, list):
        messages = [Message.from_response(m) for m in reversed(result)]
        for msg in messages:
            print(msg.display())
            print()
        print(f"--- {len(messages)} message(s) ---")
    else:
        print("No messages found.")


@app.command()
def channels(
    guild_id: Annotated[str | None, typer.Option("--guild-id", help="Guild ID (overrides default)")] = None,
) -> None:
    """List guild channels."""
    effective_guild_id = guild_id or _guild_id
    if not effective_guild_id:
        print("Error: DISCORD_GUILD_ID environment variable is not set and --guild-id not provided.", file=sys.stderr)
        raise typer.Exit(code=1)

    result = api_request("GET", f"/guilds/{effective_guild_id}/channels")
    if result and isinstance(result, list):
        parsed = [Channel.from_response(ch) for ch in result]

        cat_names: dict[str, str] = {}
        for ch in parsed:
            if ch.type == 4:
                cat_names[ch.id] = ch.name

        categories: dict[str | None, list[Channel]] = {}
        for ch in parsed:
            if ch.type == 4:
                continue
            categories.setdefault(ch.parent_id, []).append(ch)

        for parent_id in [None, *sorted(cat_names.keys(), key=lambda k: cat_names.get(k, ""))]:
            if parent_id is None:
                header = "[No Category]"
            else:
                header = f"[{cat_names.get(parent_id, parent_id)}]"

            group = categories.get(parent_id, [])
            if not group:
                continue

            print(header)
            for ch in sorted(group, key=lambda c: c.position):
                print(ch.display())
            print()

        print(f"--- {len(parsed)} channel(s) ---")
    else:
        print("No channels found.")


@app.command()
def threads(
    channel_id: Annotated[str | None, typer.Option("--channel-id", help="Filter by parent channel ID")] = None,
    guild_id: Annotated[str | None, typer.Option("--guild-id", help="Guild ID (overrides default)")] = None,
) -> None:
    """List active threads in the guild."""
    effective_guild_id = guild_id or _guild_id
    if not effective_guild_id:
        print("Error: DISCORD_GUILD_ID environment variable is not set and --guild-id not provided.", file=sys.stderr)
        raise typer.Exit(code=1)

    result = api_request("GET", f"/guilds/{effective_guild_id}/threads/active")
    if not result or not isinstance(result, dict):
        print("No active threads found.")
        return

    raw_threads: list[dict[str, Any]] = result.get("threads", [])
    parsed = [ActiveThread.from_response(t) for t in raw_threads]

    if channel_id:
        parsed = [t for t in parsed if t.parent_id == channel_id]

    if not parsed:
        print("No active threads found.")
        return

    # Resolve parent channel names for display
    parent_ids = {t.parent_id for t in parsed if t.parent_id}
    parent_names: dict[str, str] = {}
    if parent_ids:
        guild_channels = api_request("GET", f"/guilds/{effective_guild_id}/channels")
        if guild_channels and isinstance(guild_channels, list):
            for ch in guild_channels:
                ch_id = ch.get("id", "")
                if ch_id in parent_ids:
                    parent_names[ch_id] = ch.get("name", ch_id)

    # Group by parent channel
    groups: dict[str | None, list[ActiveThread]] = {}
    for t in parsed:
        groups.setdefault(t.parent_id, []).append(t)

    for parent_id, group_threads in sorted(groups.items(), key=lambda x: parent_names.get(x[0] or "", "")):
        header = f"#{parent_names.get(parent_id or '', parent_id or 'unknown')}"
        print(f"[{header}]")
        for t in sorted(group_threads, key=lambda x: x.thread_metadata.create_timestamp or "", reverse=True):
            parent_name = parent_names.get(t.parent_id or "") if not channel_id else None
            print(t.display(parent_name))
        print()

    print(f"--- {len(parsed)} active thread(s) ---")


@app.command()
def thread(
    channel_id: Annotated[str, typer.Option("--channel-id", help="Parent channel ID")],
    name: Annotated[str, typer.Option("--name", help="Thread name")],
    message_id: Annotated[str | None, typer.Option("--message-id", help="Message ID to create thread from")] = None,
    thread_type: Annotated[ThreadType, typer.Option("--type", help="Thread type")] = ThreadType.PUBLIC,
) -> None:
    """Create a thread."""
    if message_id:
        result = api_request(
            "POST",
            f"/channels/{channel_id}/messages/{message_id}/threads",
            body={"name": name},
        )
    else:
        result = api_request(
            "POST",
            f"/channels/{channel_id}/threads",
            body={"name": name, "type": thread_type.value},
        )
    if result and isinstance(result, dict):
        t = Thread.from_response(result)
        print(t.display())


@app.command()
def react(
    channel_id: Annotated[str, typer.Option("--channel-id", help="Channel containing the message")],
    message_id: Annotated[str, typer.Option("--message-id", help="Message ID to react to")],
    emoji: Annotated[str, typer.Option("--emoji", help="Emoji name (e.g. thumbsup, fire)")],
) -> None:
    """React to a message with an emoji."""
    encoded_emoji = urllib.parse.quote(emoji, safe="")
    _ = api_request(
        "PUT",
        f"/channels/{channel_id}/messages/{message_id}/reactions/{encoded_emoji}/@me",
    )
    print(f"Reacted with :{emoji}: on msg:{message_id}")


@app.command("send-file")
def send_file(
    file: Annotated[str, typer.Option("--file", help="Path to file to upload")],
    channel_id: ChannelIdOpt = None,
    thread_id: ThreadIdOpt = None,
    user_id: UserIdOpt = None,
    message: Annotated[str | None, typer.Option("--message", help="Optional text message with the file")] = None,
) -> None:
    """Send a file to a channel, thread, or DM."""
    target = resolve_channel_id(channel_id=channel_id, thread_id=thread_id, user_id=user_id)

    if not Path(file).is_file():
        print(f"Error: file not found: {file}", file=sys.stderr)
        raise typer.Exit(code=1)

    fields: dict[str, str] = {}
    if message:
        payload = json.dumps({"content": message})
        fields["payload_json"] = payload

    raw_body, content_type = build_multipart(fields, file)

    result = api_request(
        "POST",
        f"/channels/{target}/messages",
        raw_body=raw_body,
        extra_headers={"Content-Type": content_type},
    )
    if result and isinstance(result, dict):
        msg = SentMessage.from_response(result)
        print(msg.display_file_sent(target))


if __name__ == "__main__":
    app()
