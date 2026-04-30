#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["certifi", "typer", "pydantic", "pyyaml"]
# ///
"""GitLab MR CLI — inline comments, discussions, and replies via GitLab API.

Covers operations that `glab` CLI does not support:
- Inline (diff) comments on specific file lines
- Structured discussion listing with file positions
- Replying to discussion threads

For everything else (create MR, list MRs, approve, merge, diff, general
comments, resolve/unresolve) use `glab` directly — it handles those well.
"""

from __future__ import annotations

import json
import os
import re
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Annotated, Any, ClassVar

import yaml

import certifi
import typer
from pydantic import BaseModel, ConfigDict

SSL_CTX = ssl.create_default_context(cafile=certifi.where())

app = typer.Typer(
    name="gitlab_cli",
    help="GitLab MR inline comments and discussions CLI.",
    no_args_is_help=True,
)

# ---------------------------------------------------------------------------
# Module-level typed state (set in @app.callback)
# ---------------------------------------------------------------------------

_token: str = ""
_base_url: str = ""
_project_id: str = ""  # URL-encoded "group/project"


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class Author(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    username: str


class DiffRefs(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    base_sha: str
    head_sha: str
    start_sha: str


class NotePosition(BaseModel):
    """Position metadata for a diff note."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    new_path: str | None = None
    old_path: str | None = None
    new_line: int | None = None
    old_line: int | None = None


class Note(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    id: int
    type: str | None = None
    body: str
    author: Author
    created_at: str
    resolvable: bool = False
    resolved: bool = False
    position: NotePosition | None = None

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> Note:
        return cls.model_validate(data)

    def display(self) -> str:
        lines = [f"Note #{self.id} by {self.author.username} ({self.created_at})"]
        if self.position and self.position.new_path:
            loc = f"  File: {self.position.new_path}"
            if self.position.new_line:
                loc += f":{self.position.new_line}"
            lines.append(loc)
        if self.resolvable:
            lines.append(f"  Resolved: {self.resolved}")
        body_preview = self.body[:300]
        if len(self.body) > 300:
            body_preview += "..."
        lines.append(f"  {body_preview}")
        return "\n".join(lines)


class Discussion(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    id: str
    individual_note: bool = False
    notes: list[Note] = []

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> Discussion:
        return cls.model_validate(data)

    def display(self) -> str:
        if not self.notes:
            return f"Discussion {self.id}: (empty)"

        first = self.notes[0]
        lines = [f"Discussion {self.id}"]
        if first.position and first.position.new_path:
            loc = f"  {first.position.new_path}"
            if first.position.new_line:
                loc += f":{first.position.new_line}"
            lines.append(loc)
        if first.resolvable:
            lines.append(f"  Resolved: {first.resolved}")
        lines.append(f"  [{len(self.notes)} note(s)]")

        for note in self.notes:
            body_preview = note.body[:200]
            if len(note.body) > 200:
                body_preview += "..."
            lines.append(f"  @{note.author.username} (#{note.id}): {body_preview}")
        return "\n".join(lines)


class MRInfo(BaseModel):
    """Minimal MR info needed for diff_refs."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    iid: int
    diff_refs: DiffRefs | None = None

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> MRInfo:
        return cls.model_validate(data)


class ReposConfig(BaseModel):
    """Config for the mrs command — list of repo paths to scan."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    repos: list[str]


class MRSummary(BaseModel):
    """Summary of an open merge request for the mrs dashboard."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    iid: int
    title: str
    author: Author
    updated_at: str

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> MRSummary:
        return cls.model_validate(data)

    def display(self) -> str:
        date = self.updated_at[:10]
        title = self.title[:80] if len(self.title) > 80 else self.title
        return f"!{self.iid:<5} {self.author.username:<12} {date}  {title}"


# ---------------------------------------------------------------------------
# Shared option aliases
# ---------------------------------------------------------------------------

MRNumberOpt = Annotated[int, typer.Option("--mr", help="Merge request IID")]


# ---------------------------------------------------------------------------
# Auto-detection helpers
# ---------------------------------------------------------------------------


def _detect_gitlab_host() -> str:
    """Detect GitLab host from glab config."""
    try:
        result = subprocess.run(
            ["glab", "config", "get", "host"],
            capture_output=True,
            text=True,
            check=True,
        )
        host = result.stdout.strip()
        if host:
            return host
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Fallback: parse git remote
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        url = result.stdout.strip()
        # SSH: git@host:group/repo.git
        match = re.match(r"git@([^:]+):", url)
        if match:
            return match.group(1)
        # HTTPS: https://host/group/repo.git
        match = re.match(r"https?://([^/]+)/", url)
        if match:
            return match.group(1)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    print("Error: Cannot detect GitLab host. Set git remote or configure glab.", file=sys.stderr)
    raise typer.Exit(code=1)


def _detect_project_path() -> str:
    """Detect project path (group/repo) from git remote."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
        url = result.stdout.strip()
        # SSH: git@host:group/repo.git
        match = re.match(r"git@[^:]+:(.+?)(?:\.git)?$", url)
        if match:
            return match.group(1)
        # HTTPS: https://host/group/repo.git
        match = re.match(r"https?://[^/]+/(.+?)(?:\.git)?$", url)
        if match:
            return match.group(1)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return ""


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


class GitLabAPIError(Exception):
    """Raised when a GitLab API request fails."""

    def __init__(self, status: int, message: str) -> None:
        self.status = status
        self.message = message
        super().__init__(f"{status}: {message}")


def api_request(
    path: str,
    *,
    method: str = "GET",
    data: dict[str, Any] | None = None,
) -> Any:  # noqa: ANN401
    """Make a GitLab API request.

    Args:
        path: API path relative to /api/v4/ (e.g., "projects/:id/merge_requests").
        method: HTTP method.
        data: JSON body (for POST/PUT).

    Raises:
        GitLabAPIError: On HTTP error responses.
    """
    resolved_path = path.replace(":id", _project_id)
    url = f"{_base_url}/api/v4/{resolved_path}"

    headers: dict[str, str] = {"PRIVATE-TOKEN": _token}

    body: bytes | None = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data).encode()

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=SSL_CTX) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        try:
            err: dict[str, Any] = json.loads(error_body)
            msg = str(err.get("message", err.get("error", error_body)))
        except json.JSONDecodeError:
            msg = error_body
        raise GitLabAPIError(e.code, msg) from e


def _get_diff_refs(mr_iid: int) -> DiffRefs:
    """Fetch diff_refs for a merge request — needed for inline comments."""
    try:
        resp: dict[str, Any] = api_request(f"projects/:id/merge_requests/{mr_iid}")
    except GitLabAPIError as e:
        print(f"Error fetching MR !{mr_iid}: {e}", file=sys.stderr)
        raise typer.Exit(code=1)
    mr = MRInfo.from_response(resp)
    if not mr.diff_refs:
        print(f"Error: MR !{mr_iid} has no diff_refs (possibly not yet diffable).", file=sys.stderr)
        raise typer.Exit(code=1)
    return mr.diff_refs


def _build_position(
    refs: DiffRefs,
    path: str,
    line: int,
    *,
    old_line: int | None = None,
    old_path: str | None = None,
) -> dict[str, Any]:
    """Build position dict for an inline comment.

    Always sets old_path — GitLab requires it to compute a valid line_code,
    even for new files (where old_path == new_path).
    """
    pos: dict[str, Any] = {
        "base_sha": refs.base_sha,
        "start_sha": refs.start_sha,
        "head_sha": refs.head_sha,
        "position_type": "text",
        "new_path": path,
    }
    if old_line is not None:
        # Commenting on a removed line
        resolved_old_path = old_path or path
        pos["old_path"] = resolved_old_path
        pos["old_line"] = old_line
    else:
        # Commenting on an added/existing line
        pos["new_line"] = line
        pos["old_path"] = old_path or path

    return pos


# ---------------------------------------------------------------------------
# App callback — validate token and detect project
# ---------------------------------------------------------------------------


@app.callback()
def main_callback(
    project: Annotated[str | None, typer.Option(help="Project path (group/repo). Auto-detected from git remote.")] = None,
    host: Annotated[str | None, typer.Option(help="GitLab host. Auto-detected from glab config.")] = None,
) -> None:
    """GitLab MR inline comments and discussions CLI."""
    global _token, _base_url, _project_id  # noqa: PLW0603

    _token = os.environ.get("GITLAB_TOKEN", "")
    if not _token:
        # Try glab's stored token
        try:
            result = subprocess.run(
                ["glab", "auth", "status", "-t"],
                capture_output=True,
                text=True,
            )
            # glab prints "Token: glpat-..." to stderr
            for line in result.stderr.splitlines():
                if "Token:" in line:
                    _token = line.split("Token:")[-1].strip()
                    break
        except FileNotFoundError:
            pass

    if not _token:
        print("Error: Set GITLAB_TOKEN or authenticate via `glab auth login`.", file=sys.stderr)
        raise typer.Exit(code=1)

    gitlab_host = host or _detect_gitlab_host()
    _base_url = f"https://{gitlab_host}"

    project_path = project or _detect_project_path()
    if project_path:
        _project_id = urllib.parse.quote(project_path, safe="")
    # If project_path is empty, _project_id stays "" — commands that need it
    # (those using :id in api_request) will fail with a clear API error.
    # Commands like `mrs` that build their own paths work without a project.


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def discussions(
    mr: MRNumberOpt,
    inline_only: Annotated[bool, typer.Option(help="Show only inline (diff) discussions")] = False,
    unresolved: Annotated[bool, typer.Option(help="Show only unresolved discussions")] = False,
) -> None:
    """List discussions on a merge request with file positions and thread structure."""
    try:
        resp: list[dict[str, Any]] = api_request(f"projects/:id/merge_requests/{mr}/discussions")
    except GitLabAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)

    results: list[Discussion] = []
    for item in resp:
        disc = Discussion.from_response(item)
        if disc.individual_note and not disc.notes:
            continue
        if inline_only and not (disc.notes and disc.notes[0].position and disc.notes[0].position.new_path):
            continue
        if unresolved and disc.notes and not any(n.resolvable and not n.resolved for n in disc.notes):
            continue
        results.append(disc)

    if not results:
        print("No discussions found.")
        return

    for disc in results:
        print(disc.display())
        print()


@app.command()
def inline_comment(
    mr: MRNumberOpt,
    path: Annotated[str, typer.Option(help="File path in the diff")],
    line: Annotated[int, typer.Option(help="Line number in the new version of the file")],
    text: Annotated[str, typer.Argument(help="Comment body (supports markdown)")],
    old_line: Annotated[int | None, typer.Option(help="Line in old version (for removed lines)")] = None,
) -> None:
    """Post an inline comment on a specific file and line in an MR diff.

    This creates a new discussion thread anchored to the diff. The comment
    appears directly on the file in the MR's Changes tab.
    """
    refs = _get_diff_refs(mr)
    position = _build_position(refs, path, line, old_line=old_line)

    try:
        resp: dict[str, Any] = api_request(
            f"projects/:id/merge_requests/{mr}/discussions",
            method="POST",
            data={"body": text, "position": position},
        )
    except GitLabAPIError as e:
        print(f"Error {e}", file=sys.stderr)
        raise typer.Exit(code=1)

    disc = Discussion.from_response(resp)
    if disc.notes:
        print(f"Posted inline comment #{disc.notes[0].id} on {path}:{line}")
        print(disc.display())
    else:
        print(f"Discussion created: {disc.id}")


@app.command()
def reply(
    mr: MRNumberOpt,
    discussion_id: Annotated[str, typer.Option(help="Discussion ID to reply to")],
    text: Annotated[str, typer.Argument(help="Reply body (supports markdown)")],
) -> None:
    """Reply to an existing discussion thread on an MR."""
    try:
        resp: dict[str, Any] = api_request(
            f"projects/:id/merge_requests/{mr}/discussions/{discussion_id}/notes",
            method="POST",
            data={"body": text},
        )
    except GitLabAPIError as e:
        print(f"Error: {e}", file=sys.stderr)
        raise typer.Exit(code=1)
    note = Note.from_response(resp)
    print(f"Reply #{note.id} added to discussion {discussion_id}")
    print(note.display())


@app.command()
def batch_inline(
    mr: MRNumberOpt,
    comments_json: Annotated[str, typer.Argument(help='JSON array: [{"path": "...", "line": N, "body": "..."}]')],
) -> None:
    """Post multiple inline comments at once on an MR.

    Fetches diff_refs once and posts all comments. Accepts a JSON array
    as a positional argument. Each object needs: path, line, body.
    Optional: old_path, old_line.
    """
    try:
        comments: list[dict[str, Any]] = json.loads(comments_json)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON — {e}", file=sys.stderr)
        raise typer.Exit(code=1)

    if not comments:
        print("No comments to post.")
        return

    refs = _get_diff_refs(mr)
    posted = 0
    failed = 0

    for c in comments:
        path = c.get("path", "")
        line = c.get("line", 0)
        body = c.get("body", "")

        if not path or not body:
            print(f"  Skipping invalid comment (missing path or body): {c}", file=sys.stderr)
            failed += 1
            continue

        position = _build_position(
            refs,
            path,
            line,
            old_line=c.get("old_line"),
            old_path=c.get("old_path"),
        )

        try:
            resp: dict[str, Any] = api_request(
                f"projects/:id/merge_requests/{mr}/discussions",
                method="POST",
                data={"body": body, "position": position},
            )
            disc = Discussion.from_response(resp)
            note_id = disc.notes[0].id if disc.notes else "?"
            print(f"  #{note_id} -> {path}:{line}")
            posted += 1
        except GitLabAPIError as e:
            print(f"  FAIL {path}:{line} -> {e}", file=sys.stderr)
            failed += 1

    print(f"\nPosted {posted}/{len(comments)} inline comments.", end="")
    if failed:
        print(f" ({failed} failed)", end="")
    print()


@app.command()
def mrs() -> None:
    """List open merge requests across all configured repos."""
    config_path = Path(__file__).parent / "repos.yaml"
    if not config_path.exists():
        print(f"Error: Config not found: {config_path}", file=sys.stderr)
        raise typer.Exit(code=1)

    try:
        raw = yaml.safe_load(config_path.read_text())
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML in {config_path}: {e}", file=sys.stderr)
        raise typer.Exit(code=1)

    config = ReposConfig.model_validate(raw)
    total = 0

    for repo_path in config.repos:
        encoded = urllib.parse.quote(repo_path, safe="")
        try:
            resp: list[dict[str, Any]] = api_request(
                f"projects/{encoded}/merge_requests?state=opened&per_page=100",
            )
        except GitLabAPIError as e:
            print(f"=== {repo_path} ===")
            print(f"  Error: {e}")
            print()
            continue

        mrs_list = [MRSummary.from_response(item) for item in resp]

        if mrs_list:
            print(f"=== {repo_path} ({len(mrs_list)} open) ===")
            for mr in mrs_list:
                print(mr.display())
        else:
            print(f"=== {repo_path} ===")
            print("No open merge requests.")
        print()
        total += len(mrs_list)

    print(f"Total: {total} open MRs across {len(config.repos)} repos")


if __name__ == "__main__":
    app()
