#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["certifi", "typer", "pydantic", "rich"]
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
from rich.console import Console, RenderableType
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

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

THREAD_TYPES: set[int] = {10, 11, 12}

console = Console()


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

    def display(self) -> Text:
        text = Text()
        text.append("  📎 ", style="dim")
        text.append(self.filename, style="green bold")
        if self.url:
            text.append(f" — {self.url}", style="dim")
        return text


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

    def display(self) -> Text:
        text = Text()
        if self.title:
            text.append("  [embed] ", style="dim")
            text.append(self.title, style="yellow italic")
            if self.url:
                text.append(f" — {self.url}", style="dim")
        elif self.url:
            text.append(f"  [embed] {self.url}", style="dim yellow")
        if self.description:
            for desc_line in self.description.split("\n"):
                text.append(f"\n    {desc_line}")
        for field in self.fields:
            text.append(f"\n    {field.name}: ", style="bold")
            text.append(field.value)
        return text


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

    def display(self) -> Panel:
        ts = self.timestamp[:19].replace("T", " ")
        body = Text()
        if self.content:
            body.append(self.content)
        for embed in self.embeds:
            if body.plain:
                body.append("\n")
            body.append_text(embed.display())
        for att in self.attachments:
            if body.plain:
                body.append("\n")
            body.append_text(att.display())

        title = Text()
        title.append(self.author.username, style="bold cyan")
        title.append(f"  {ts}", style="dim cyan")

        return Panel(
            body,
            title=title,
            title_align="left",
            subtitle=Text(f"msg:{self.id}", style="dim"),
            subtitle_align="right",
            expand=True,
            padding=(0, 1),
        )


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

    def display(self) -> Text:
        text = Text()
        text.append(f"#{self.name}", style="bold blue")
        text.append(f"  (id:{self.id}, type:{self.type_name})", style="dim")
        return text


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

    def display(self) -> Text:
        text = Text()
        text.append("Created thread: ", style="bold green")
        text.append(self.name, style="bold magenta")
        text.append(f" (id:{self.id})", style="dim")
        return text


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

    def display(self, parent_name: str | None = None) -> Text:
        created = ""
        if self.thread_metadata.create_timestamp:
            created = self.thread_metadata.create_timestamp[:19].replace("T", " ")
        text = Text()
        text.append("💬 ", style="bold")
        text.append(self.name, style="bold magenta")
        text.append(f"  (id:{self.id})", style="dim")
        if parent_name:
            text.append(f" in ", style="dim")
            text.append(f"#{parent_name}", style="dim blue")
        text.append("\n   msgs:", style="dim")
        text.append(str(self.message_count), style="cyan")
        text.append(" | members:", style="dim")
        text.append(str(self.member_count), style="cyan")
        if created:
            text.append(f" | created:{created}", style="dim")
        return text


class SentMessage(BaseModel):
    """Result of sending/editing a message."""

    model_config = ConfigDict(extra="ignore")  # pyright: ignore[reportUnannotatedClassAttribute]

    id: str
    content: str = ""
    attachments: list[Attachment] = []

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> SentMessage:
        return cls.model_validate(data)

    def display_sent(self, target: str) -> Text:
        text = Text()
        text.append("Sent ", style="bold green")
        text.append(f"(msg:{self.id})", style="dim")
        text.append(" to channel:", style="dim")
        text.append(target, style="blue")
        if self.content:
            text.append(f"\n  {self.content}", style="dim")
        return text

    def display_edited(self, channel_id: str) -> Text:
        text = Text()
        text.append("Edited ", style="bold yellow")
        text.append(f"(msg:{self.id})", style="dim")
        text.append(" in channel:", style="dim")
        text.append(channel_id, style="blue")
        if self.content:
            text.append(f"\n  {self.content}", style="dim")
        return text

    def display_file_sent(self, target: str) -> Text:
        att_info = f", {len(self.attachments)} attachment(s)" if self.attachments else ""
        text = Text()
        text.append("Sent file ", style="bold green")
        text.append(f"(msg:{self.id})", style="dim")
        text.append(" to channel:", style="dim")
        text.append(f"{target}{att_info}", style="blue")
        if self.content:
            text.append(f"\n  {self.content}", style="dim")
        return text


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


def _summary(text: str) -> RenderableType:
    """Render a dim summary/footer line."""
    return Text(text, style="dim")


def _require_guild_id(guild_id: str | None = None) -> str:
    """Return effective guild ID or exit."""
    effective = guild_id or _guild_id
    if not effective:
        print("Error: DISCORD_GUILD_ID environment variable is not set and --guild-id not provided.", file=sys.stderr)
        raise typer.Exit(code=1)
    return effective


def _try_fetch_message(channel_id: str, message_id: str) -> dict[str, Any] | None:
    """Try to fetch a single message. Returns None instead of exiting on 404/403."""
    url = f"{BASE_URL}/channels/{channel_id}/messages/{message_id}"
    headers = {
        "Authorization": f"Bot {_token}",
        "User-Agent": "DiscordCLI/1.0",
    }
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as resp:
            body = resp.read()
            if body:
                result: dict[str, Any] = json.loads(body)
                return result
    except urllib.error.HTTPError:
        pass
    except urllib.error.URLError:
        pass
    return None


def resolve_message(
    message_id: str,
    channel_id: str | None = None,
    guild_id: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Resolve a message by ID, optionally searching across the guild.

    Returns (message_json, channel_id).
    """
    # Strategy 1: direct fetch if channel_id is known
    if channel_id:
        result = api_request("GET", f"/channels/{channel_id}/messages/{message_id}")
        if result and isinstance(result, dict):
            return result, channel_id
        print(f"Error: message {message_id} not found in channel {channel_id}.", file=sys.stderr)
        raise typer.Exit(code=1)

    effective_guild = _require_guild_id(guild_id)

    # Strategy 2: guild search API
    params = urllib.parse.urlencode({"min_id": str(int(message_id) - 1), "max_id": str(int(message_id) + 1)})
    try:
        search_result = api_request("GET", f"/guilds/{effective_guild}/messages/search?{params}")
        if search_result and isinstance(search_result, dict):
            for group in search_result.get("messages", []):
                for msg in group:
                    if isinstance(msg, dict) and msg.get("id") == message_id:
                        return msg, str(msg["channel_id"])
    except SystemExit:
        pass  # search may fail due to permissions, fall through

    # Strategy 3: brute-force — try all channels and active threads
    console.print(Text("Message not found via search, scanning channels...", style="dim yellow"))

    candidate_ids: list[str] = []

    # Gather active thread IDs
    try:
        threads_resp = api_request("GET", f"/guilds/{effective_guild}/threads/active")
        if threads_resp and isinstance(threads_resp, dict):
            for t in threads_resp.get("threads", []):
                if isinstance(t, dict) and "id" in t:
                    candidate_ids.append(str(t["id"]))
    except SystemExit:
        pass

    # Gather channel IDs
    try:
        channels_resp = api_request("GET", f"/guilds/{effective_guild}/channels")
        if channels_resp and isinstance(channels_resp, list):
            for ch in channels_resp:
                if isinstance(ch, dict) and "id" in ch:
                    candidate_ids.append(str(ch["id"]))
    except SystemExit:
        pass

    total = len(candidate_ids)
    for i, cid in enumerate(candidate_ids, 1):
        if i % 20 == 0:
            console.print(Text(f"  Checked {i}/{total} channels...", style="dim"))
        msg_data = _try_fetch_message(cid, message_id)
        if msg_data is not None:
            console.print(Text(f"  Found in channel {cid}", style="dim green"))
            return msg_data, cid

    print(f"Error: message {message_id} not found in any accessible channel.", file=sys.stderr)
    raise typer.Exit(code=1)


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
        console.print(msg.display_sent(target))


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
        console.print(msg.display_edited(channel_id))


def _fetch_thread_starter(channel_id: str) -> Message | None:
    """If channel_id is a thread, fetch the starter message from the parent channel."""
    ch_info = api_request("GET", f"/channels/{channel_id}")
    if not ch_info or not isinstance(ch_info, dict):
        return None
    ch_type = ch_info.get("type", 0)
    if ch_type not in THREAD_TYPES:
        return None
    parent_id = ch_info.get("parent_id")
    if not parent_id:
        return None
    try:
        starter = api_request("GET", f"/channels/{parent_id}/messages/{channel_id}")
        if starter and isinstance(starter, dict):
            return Message.from_response(starter)
    except SystemExit:
        pass
    return None


@app.command()
def get(
    channel_id: Annotated[str, typer.Option("--channel-id", help="Channel to read from")],
    limit: Annotated[int, typer.Option("--limit", help="Number of messages (default: 20, max: 100)")] = 20,
) -> None:
    """Get recent messages from a channel."""
    starter = _fetch_thread_starter(channel_id)
    if starter:
        console.print(Rule("thread starter", style="cyan"))
        console.print(starter.display())

    params = urllib.parse.urlencode({"limit": limit})
    result = api_request("GET", f"/channels/{channel_id}/messages?{params}")
    if result and isinstance(result, list):
        if starter:
            console.print(Rule("thread replies", style="cyan"))
        messages = [Message.from_response(m) for m in reversed(result)]
        for msg in messages:
            console.print(msg.display())
        total = len(messages) + (1 if starter else 0)
        console.print(_summary(f"--- {total} message(s) ---"))
    else:
        console.print("No messages found.")


@app.command("get-message")
def get_message(
    message_id: Annotated[str, typer.Option("--message-id", help="Message ID to fetch")],
    channel_id: Annotated[str | None, typer.Option("--channel-id", help="Channel ID (optional — auto-resolves if omitted)")] = None,
) -> None:
    """Fetch and display a single message by ID."""
    msg_data, resolved_cid = resolve_message(message_id, channel_id=channel_id)
    msg = Message.from_response(msg_data)
    console.print(msg.display())
    console.print(_summary(f"channel:{resolved_cid}"))


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
                header = "No Category"
            else:
                header = cat_names.get(parent_id, parent_id)

            group = categories.get(parent_id, [])
            if not group:
                continue

            table = Table(title=header, title_style="bold yellow", expand=True, show_header=True, show_lines=False)
            table.add_column("Name", style="bold blue")
            table.add_column("ID", style="dim")
            table.add_column("Type", style="cyan")

            for ch in sorted(group, key=lambda c: c.position):
                table.add_row(f"#{ch.name}", ch.id, ch.type_name)

            console.print(table)
            console.print()

        console.print(_summary(f"--- {len(parsed)} channel(s) ---"))
    else:
        console.print("No channels found.")


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
        console.print("No active threads found.")
        return

    raw_threads: list[dict[str, Any]] = result.get("threads", [])
    parsed = [ActiveThread.from_response(t) for t in raw_threads]

    if channel_id:
        parsed = [t for t in parsed if t.parent_id == channel_id]

    if not parsed:
        console.print("No active threads found.")
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

        table = Table(title=header, title_style="bold yellow", expand=True, show_header=True, show_lines=False)
        table.add_column("Name", style="bold magenta")
        table.add_column("ID", style="dim")
        table.add_column("Messages", justify="right", style="cyan")
        table.add_column("Members", justify="right", style="cyan")
        table.add_column("Created", style="dim")

        for t in sorted(group_threads, key=lambda x: x.thread_metadata.create_timestamp or "", reverse=True):
            created = ""
            if t.thread_metadata.create_timestamp:
                created = t.thread_metadata.create_timestamp[:19].replace("T", " ")
            name = f"💬 {t.name}"
            if not channel_id:
                parent_name = parent_names.get(t.parent_id or "")
                if parent_name:
                    name += f" (in #{parent_name})"
            table.add_row(name, t.id, str(t.message_count), str(t.member_count), created)

        console.print(table)
        console.print()

    console.print(_summary(f"--- {len(parsed)} active thread(s) ---"))


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
        console.print(t.display())


@app.command()
def rename(
    thread_id: Annotated[str, typer.Option("--thread-id", help="Thread ID to rename")],
    name: Annotated[str, typer.Option("--name", help="New thread name")],
) -> None:
    """Rename a thread."""
    result = api_request("PATCH", f"/channels/{thread_id}", body={"name": name})
    if result and isinstance(result, dict):
        t = Thread.from_response(result)
        text = Text()
        text.append("Renamed thread to: ", style="bold yellow")
        text.append(t.name, style="bold magenta")
        text.append(f" (id:{t.id})", style="dim")
        console.print(text)


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
    text = Text()
    text.append("Reacted with ", style="bold green")
    text.append(f":{emoji}:", style="bold yellow")
    text.append(f" on msg:{message_id}", style="dim")
    console.print(text)


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
        console.print(msg.display_file_sent(target))


@app.command()
def download(
    message_id: Annotated[str, typer.Option("--message-id", help="Message ID containing attachments")],
    channel_id: Annotated[str | None, typer.Option("--channel-id", help="Channel ID (optional — auto-resolves if omitted)")] = None,
    output: Annotated[str | None, typer.Option("--output", help="Output path (default: current dir with original filename)")] = None,
    index: Annotated[int, typer.Option("--index", help="Attachment index to download (default: 0 = first, -1 = all)")] = -1,
) -> None:
    """Download attachments from a message."""
    msg_data, resolved_cid = resolve_message(message_id, channel_id=channel_id)
    msg = Message.from_response(msg_data)

    if not msg.attachments:
        console.print(Text("No attachments found on this message.", style="yellow"))
        raise typer.Exit(code=1)

    if index >= 0:
        if index >= len(msg.attachments):
            print(f"Error: attachment index {index} out of range (message has {len(msg.attachments)}).", file=sys.stderr)
            raise typer.Exit(code=1)
        targets = [msg.attachments[index]]
    else:
        targets = list(msg.attachments)

    for att in targets:
        if not att.url:
            console.print(Text(f"  Skipping {att.filename} — no URL", style="dim yellow"))
            continue

        if output and len(targets) == 1:
            dest = Path(output)
        else:
            dest = Path(output or ".") / att.filename
            if output and Path(output).is_dir():
                dest = Path(output) / att.filename

        req = urllib.request.Request(att.url, method="GET", headers={"User-Agent": "DiscordCLI/1.0"})
        try:
            with urllib.request.urlopen(req, context=SSL_CTX) as resp:
                data = resp.read()
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                text = Text()
                text.append("  ✓ ", style="bold green")
                text.append(att.filename, style="bold green")
                text.append(f" → {dest} ({len(data):,} bytes)", style="dim")
                console.print(text)
        except urllib.error.HTTPError as e:
            print(f"Error downloading {att.filename}: HTTP {e.code}", file=sys.stderr)
        except urllib.error.URLError as e:
            print(f"Error downloading {att.filename}: {e.reason}", file=sys.stderr)

    console.print(_summary(f"channel:{resolved_cid} | msg:{message_id}"))


if __name__ == "__main__":
    app()
