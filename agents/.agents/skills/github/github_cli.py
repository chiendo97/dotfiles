#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["certifi", "pyjwt[crypto]", "typer", "pydantic"]
# ///
"""GitHub PR CLI - Manage pull requests via the GitHub API."""

from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from enum import Enum
from typing import Annotated, Any, ClassVar

import certifi
import typer
from pydantic import BaseModel, ConfigDict

SSL_CTX = ssl.create_default_context(cafile=certifi.where())

BASE_URL = "https://api.github.com"
GRAPHQL_URL = f"{BASE_URL}/graphql"

app = typer.Typer(
    name="github_cli",
    help="GitHub PR management CLI",
    no_args_is_help=True,
)

# ---------------------------------------------------------------------------
# Module-level typed state (set in @app.callback)
# ---------------------------------------------------------------------------

_token: str = ""


# ---------------------------------------------------------------------------
# Enums (for write parameters only)
# ---------------------------------------------------------------------------


class PRState(str, Enum):
    open = "open"
    closed = "closed"


class ReviewEvent(str, Enum):
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    COMMENT = "COMMENT"


class DiffSide(str, Enum):
    RIGHT = "RIGHT"
    LEFT = "LEFT"


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------


class User(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    login: str


class BranchRef(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    ref: str
    sha: str


class PullRequest(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    number: int
    title: str
    state: str
    draft: bool = False
    user: User
    head: BranchRef
    base: BranchRef
    html_url: str
    created_at: str
    updated_at: str
    body: str | None = None

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> PullRequest:
        return cls.model_validate(data)

    def display(self) -> str:
        lines = [
            f"PR #{self.number}: {self.title}",
            f"  State:   {self.state}  {'(draft)' if self.draft else ''}".rstrip(),
            f"  Author:  {self.user.login}",
            f"  Branch:  {self.head.ref} -> {self.base.ref}",
            f"  URL:     {self.html_url}",
            f"  Created: {self.created_at}",
            f"  Updated: {self.updated_at}",
        ]
        if self.body:
            body_preview = self.body[:200]
            if len(self.body) > 200:
                body_preview += "..."
            lines.append(f"  Body:    {body_preview}")
        return "\n".join(lines)


class ChangedFile(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    filename: str
    status: str
    additions: int = 0
    deletions: int = 0

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> ChangedFile:
        return cls.model_validate(data)

    def display(self) -> str:
        return f"  {self.status:10s} +{self.additions}/-{self.deletions}  {self.filename}"


class Comment(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    id: int
    user: User
    created_at: str
    body: str
    path: str | None = None
    line: int | None = None
    original_line: int | None = None
    in_reply_to_id: int | None = None

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> Comment:
        return cls.model_validate(data)

    def display(self) -> str:
        lines = [
            f"Comment #{self.id} by {self.user.login} ({self.created_at})",
        ]
        if self.path:
            line_info = f"  File: {self.path}"
            if self.line:
                line_info += f":{self.line}"
            elif self.original_line:
                line_info += f":{self.original_line}"
            lines.append(line_info)
        if self.in_reply_to_id:
            lines.append(f"  In reply to: #{self.in_reply_to_id}")
        lines.append(f"  {self.body}")
        return "\n".join(lines)


class Review(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")
    id: int
    state: str
    body: str | None = None

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> Review:
        return cls.model_validate(data)

    def display(self) -> str:
        lines = [f"Review #{self.id} submitted: {self.state}"]
        if self.body:
            lines.append(f"  {self.body}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Shared option type aliases
# ---------------------------------------------------------------------------

OwnerOpt = Annotated[str, typer.Option(help="Repository owner")]
RepoOpt = Annotated[str, typer.Option(help="Repository name")]
NumberOpt = Annotated[int, typer.Option(help="Pull request number")]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def _get_installation_token(app_id: str, installation_id: str, private_key: str) -> str:
    """Generate a GitHub App installation access token via JWT."""
    import time

    import jwt  # pyright: ignore[reportMissingImports]

    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (10 * 60),
        "iss": app_id,
    }
    encoded_jwt: str = jwt.encode(payload, private_key, algorithm="RS256")  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    url = f"{BASE_URL}/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {encoded_jwt}",
        "Accept": "application/vnd.github+json",
    }
    req = urllib.request.Request(url, data=b"", headers=headers, method="POST")
    with urllib.request.urlopen(req, context=SSL_CTX) as resp:
        data: dict[str, Any] = json.loads(resp.read())
    return str(data["token"])


def _resolve_token() -> str:
    """Get GitHub token -- prefers GITHUB_TOKEN, falls back to GitHub App JWT auth."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token

    app_id = os.environ.get("GITHUB_APP_ID")
    installation_id = os.environ.get("GITHUB_APP_INSTALLATION_ID")
    private_key = os.environ.get("GITHUB_APP_PRIVATE_KEY")

    if not (app_id and installation_id and private_key):
        msg = (
            "Error: Set GITHUB_TOKEN, or all of GITHUB_APP_ID, "
            + "GITHUB_APP_INSTALLATION_ID, GITHUB_APP_PRIVATE_KEY."
        )
        print(msg, file=sys.stderr)
        raise typer.Exit(code=1)

    return _get_installation_token(app_id, installation_id, private_key)


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


def api_request(
    url: str,
    *,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    token: str | None = None,
) -> Any:  # noqa: ANN401
    """Make a GitHub API request."""
    tok = token or _token
    headers = {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = None
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
            msg = err.get("message", error_body)
        except json.JSONDecodeError:
            msg = error_body
        print(f"Error {e.code}: {msg}", file=sys.stderr)
        raise typer.Exit(code=1)


def graphql(query: str, variables: dict[str, Any] | None = None) -> Any:  # noqa: ANN401
    """Execute a GitHub GraphQL query."""
    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = dict(variables)
    return api_request(GRAPHQL_URL, method="POST", data=payload)


def _get_pr_head_sha(owner: str, repo: str, number: int) -> str:
    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls/{number}"
    pr_data: dict[str, Any] = api_request(url)
    return str(pr_data["head"]["sha"])


# ---------------------------------------------------------------------------
# App callback — validate token once
# ---------------------------------------------------------------------------


@app.callback()
def main_callback() -> None:
    """GitHub PR management CLI."""
    global _token  # noqa: PLW0603
    _token = _resolve_token()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def create_pr(
    owner: OwnerOpt,
    repo: RepoOpt,
    title: Annotated[str, typer.Option(help="PR title")],
    head: Annotated[str, typer.Option(help="Source branch")],
    base: Annotated[str, typer.Option(help="Target branch")],
    body: Annotated[str | None, typer.Option(help="PR body")] = None,
    draft: Annotated[bool, typer.Option(help="Create as draft")] = False,
) -> None:
    """Create a pull request."""
    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls"
    data: dict[str, Any] = {
        "title": title,
        "head": head,
        "base": base,
    }
    if body is not None:
        data["body"] = body
    if draft:
        data["draft"] = True

    resp = api_request(url, method="POST", data=data)
    pr = PullRequest.from_response(resp)
    print(pr.display())


@app.command()
def update_pr(
    owner: OwnerOpt,
    repo: RepoOpt,
    number: NumberOpt,
    title: Annotated[str | None, typer.Option(help="New title")] = None,
    body: Annotated[str | None, typer.Option(help="New body")] = None,
    state: Annotated[PRState | None, typer.Option(help="New state")] = None,
    base: Annotated[str | None, typer.Option(help="New base branch")] = None,
) -> None:
    """Update an existing pull request."""
    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls/{number}"
    data: dict[str, Any] = {}
    if title is not None:
        data["title"] = title
    if body is not None:
        data["body"] = body
    if state is not None:
        data["state"] = state.value
    if base is not None:
        data["base"] = base

    if not data:
        print("Error: No update fields specified.", file=sys.stderr)
        raise typer.Exit(code=1)

    resp = api_request(url, method="PATCH", data=data)
    pr = PullRequest.from_response(resp)
    print(pr.display())


@app.command()
def list_prs(
    owner: OwnerOpt,
    repo: RepoOpt,
    state: Annotated[str, typer.Option(help="Filter by state (open/closed/all)")] = "open",
    sort: Annotated[str, typer.Option(help="Sort field")] = "updated",
    direction: Annotated[str, typer.Option(help="Sort direction (asc/desc)")] = "desc",
    head: Annotated[str | None, typer.Option(help="Filter by head branch")] = None,
    base: Annotated[str | None, typer.Option(help="Filter by base branch")] = None,
    page: Annotated[int, typer.Option(help="Page number")] = 1,
    page_size: Annotated[int, typer.Option(help="Results per page")] = 20,
) -> None:
    """List pull requests with filters."""
    params = [
        f"state={state}",
        f"sort={sort}",
        f"direction={direction}",
        f"per_page={page_size}",
        f"page={page}",
    ]
    if head is not None:
        params.append(f"head={head}")
    if base is not None:
        params.append(f"base={base}")

    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls?{'&'.join(params)}"
    resp_list: list[dict[str, Any]] = api_request(url)

    if not resp_list:
        print("No pull requests found.")
        return

    for item in resp_list:
        pr = PullRequest.from_response(item)
        print(pr.display())
        print()


@app.command()
def get_pr(
    owner: OwnerOpt,
    repo: RepoOpt,
    number: NumberOpt,
) -> None:
    """Get PR details including changed files."""
    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls/{number}"
    resp = api_request(url)
    pr = PullRequest.from_response(resp)
    print(pr.display())

    files_url = f"{url}/files?per_page=100"
    files_resp: list[dict[str, Any]] = api_request(files_url)
    if files_resp:
        files = [ChangedFile.from_response(f) for f in files_resp]
        print(f"\nFiles changed ({len(files)}):")
        for f in files:
            print(f.display())


@app.command()
def comments(
    owner: OwnerOpt,
    repo: RepoOpt,
    number: NumberOpt,
) -> None:
    """Get all comments on a PR (general and inline review comments)."""
    issue_url = f"{BASE_URL}/repos/{owner}/{repo}/issues/{number}/comments?per_page=100"
    issue_resp: list[dict[str, Any]] = api_request(issue_url)

    review_url = f"{BASE_URL}/repos/{owner}/{repo}/pulls/{number}/comments?per_page=100"
    review_resp: list[dict[str, Any]] = api_request(review_url)

    if not issue_resp and not review_resp:
        print("No comments found.")
        return

    if issue_resp:
        print("=== General Comments ===\n")
        for item in issue_resp:
            c = Comment.from_response(item)
            print(c.display())
            print()

    if review_resp:
        print("=== Review Comments ===\n")
        for item in review_resp:
            c = Comment.from_response(item)
            print(c.display())
            print()


@app.command()
def comment(
    owner: OwnerOpt,
    repo: RepoOpt,
    number: NumberOpt,
    text: Annotated[str, typer.Argument(help="Comment body")],
    path: Annotated[str | None, typer.Option(help="File path for inline comment")] = None,
    line: Annotated[int | None, typer.Option(help="Line number for inline comment")] = None,
) -> None:
    """Add a general or inline comment to a PR."""
    if path is not None:
        url = f"{BASE_URL}/repos/{owner}/{repo}/pulls/{number}/comments"
        data: dict[str, Any] = {
            "body": text,
            "path": path,
            "commit_id": _get_pr_head_sha(owner, repo, number),
        }
        if line is not None:
            data["line"] = line
            data["side"] = "RIGHT"
        else:
            data["subject_type"] = "file"
    else:
        url = f"{BASE_URL}/repos/{owner}/{repo}/issues/{number}/comments"
        data = {"body": text}

    resp = api_request(url, method="POST", data=data)
    c = Comment.from_response(resp)
    print(c.display())


@app.command()
def review(
    owner: OwnerOpt,
    repo: RepoOpt,
    number: NumberOpt,
    event: Annotated[ReviewEvent, typer.Option(help="Review event type")],
    body: Annotated[str | None, typer.Option(help="Review body")] = None,
) -> None:
    """Submit a review on a PR."""
    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls/{number}/reviews"
    data: dict[str, Any] = {"event": event.value}
    if body is not None:
        data["body"] = body

    resp = api_request(url, method="POST", data=data)
    r = Review.from_response(resp)
    print(r.display())


@app.command()
def review_comment(
    owner: OwnerOpt,
    repo: RepoOpt,
    number: NumberOpt,
    path: Annotated[str, typer.Option(help="File path")],
    line: Annotated[int, typer.Option(help="Line number")],
    text: Annotated[str, typer.Argument(help="Comment body")],
    side: Annotated[DiffSide, typer.Option(help="Diff side")] = DiffSide.RIGHT,
) -> None:
    """Create an inline review comment on a file."""
    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls/{number}/comments"
    data: dict[str, Any] = {
        "body": text,
        "path": path,
        "line": line,
        "side": side.value,
        "commit_id": _get_pr_head_sha(owner, repo, number),
    }

    resp = api_request(url, method="POST", data=data)
    c = Comment.from_response(resp)
    print(c.display())


@app.command()
def reply(
    owner: OwnerOpt,
    repo: RepoOpt,
    number: NumberOpt,
    comment_id: Annotated[int, typer.Option(help="Comment ID to reply to")],
    text: Annotated[str, typer.Argument(help="Reply body")],
) -> None:
    """Reply to a review comment thread."""
    url = (
        f"{BASE_URL}/repos/{owner}/{repo}/pulls/{number}"
        f"/comments/{comment_id}/replies"
    )
    data: dict[str, Any] = {"body": text}
    resp = api_request(url, method="POST", data=data)
    c = Comment.from_response(resp)
    print(c.display())


@app.command()
def resolve(
    owner: OwnerOpt,
    repo: RepoOpt,
    number: NumberOpt,  # noqa: ARG001  # pyright: ignore[reportUnusedParameter]
    comment_id: Annotated[int, typer.Option(help="Comment ID of the thread to resolve")],
    unresolve: Annotated[bool, typer.Option(help="Unresolve instead of resolve")] = False,
) -> None:
    """Resolve or unresolve a review thread by comment ID."""
    # Step 1: Get the node_id of the comment
    comment_url = f"{BASE_URL}/repos/{owner}/{repo}/pulls/comments/{comment_id}"
    comment_resp: dict[str, Any] = api_request(comment_url)
    node_id = comment_resp["node_id"]

    # Step 2: Find the thread node ID via GraphQL
    query = """
    query($nodeId: ID!) {
      node(id: $nodeId) {
        ... on PullRequestReviewComment {
          pullRequestReview {
            pullRequest {
              reviewThreads(last: 100) {
                nodes {
                  id
                  isResolved
                  comments(first: 1) {
                    nodes {
                      databaseId
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    result: dict[str, Any] = graphql(query, {"nodeId": node_id})

    if "errors" in result:
        print(f"GraphQL error: {result['errors']}", file=sys.stderr)
        raise typer.Exit(code=1)

    threads: list[dict[str, Any]] = (
        result.get("data", {})
        .get("node", {})
        .get("pullRequestReview", {})
        .get("pullRequest", {})
        .get("reviewThreads", {})
        .get("nodes", [])
    )

    thread_id: str | None = None
    for thread in threads:
        thread_comments: list[dict[str, Any]] = thread.get("comments", {}).get("nodes", [])
        if thread_comments and thread_comments[0].get("databaseId") == comment_id:
            thread_id = str(thread["id"])
            break

    if not thread_id:
        print("Error: Could not find review thread for this comment.", file=sys.stderr)
        raise typer.Exit(code=1)

    # Step 3: Resolve or unresolve
    if unresolve:
        mutation = """
        mutation($threadId: ID!) {
          unresolveReviewThread(input: {threadId: $threadId}) {
            thread { id isResolved }
          }
        }
        """
        action = "Unresolved"
    else:
        mutation = """
        mutation($threadId: ID!) {
          resolveReviewThread(input: {threadId: $threadId}) {
            thread { id isResolved }
          }
        }
        """
        action = "Resolved"

    mutation_result: dict[str, Any] = graphql(mutation, {"threadId": thread_id})
    if "errors" in mutation_result:
        print(f"GraphQL error: {mutation_result['errors']}", file=sys.stderr)
        raise typer.Exit(code=1)

    print(f"{action} thread for comment #{comment_id}")


if __name__ == "__main__":
    app()
