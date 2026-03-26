#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["certifi", "pyjwt[crypto]"]
# ///
"""GitHub PR CLI - Manage pull requests via the GitHub API."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from typing import Any

import certifi

SSL_CTX = ssl.create_default_context(cafile=certifi.where())


BASE_URL = "https://api.github.com"
GRAPHQL_URL = f"{BASE_URL}/graphql"


def get_token() -> str:
    """Get GitHub token — prefers GITHUB_TOKEN, falls back to GitHub App JWT auth."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token

    # Fall back to GitHub App authentication
    app_id = os.environ.get("GITHUB_APP_ID")
    installation_id = os.environ.get("GITHUB_APP_INSTALLATION_ID")
    private_key = os.environ.get("GITHUB_APP_PRIVATE_KEY")

    if not (app_id and installation_id and private_key):
        print(
            "Error: Set GITHUB_TOKEN, or all of GITHUB_APP_ID, "
            "GITHUB_APP_INSTALLATION_ID, GITHUB_APP_PRIVATE_KEY.",
            file=sys.stderr,
        )
        sys.exit(1)

    return _get_installation_token(app_id, installation_id, private_key)


def _get_installation_token(app_id: str, installation_id: str, private_key: str) -> str:
    """Generate a GitHub App installation access token via JWT."""
    import time
    import jwt

    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (10 * 60),
        "iss": app_id,
    }
    encoded_jwt = jwt.encode(payload, private_key, algorithm="RS256")

    url = f"{BASE_URL}/app/installations/{installation_id}/access_tokens"
    headers = {
        "Authorization": f"Bearer {encoded_jwt}",
        "Accept": "application/vnd.github+json",
    }
    req = urllib.request.Request(url, data=b"", headers=headers, method="POST")
    with urllib.request.urlopen(req, context=SSL_CTX) as resp:
        data = json.loads(resp.read())
    return data["token"]


def api_request(
    url: str,
    *,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    token: str | None = None,
) -> Any:
    """Make a GitHub API request."""
    token = token or get_token()
    headers = {
        "Authorization": f"Bearer {token}",
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
            err = json.loads(error_body)
            msg = err.get("message", error_body)
        except json.JSONDecodeError:
            msg = error_body
        print(f"Error {e.code}: {msg}", file=sys.stderr)
        sys.exit(1)


def graphql(query: str, variables: dict[str, Any] | None = None) -> Any:
    """Execute a GitHub GraphQL query."""
    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables
    return api_request(GRAPHQL_URL, method="POST", data=payload)


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------

def fmt_pr(pr: dict[str, Any]) -> str:
    lines = [
        f"PR #{pr['number']}: {pr['title']}",
        f"  State:   {pr['state']}  {'(draft)' if pr.get('draft') else ''}".rstrip(),
        f"  Author:  {pr['user']['login']}",
        f"  Branch:  {pr['head']['ref']} -> {pr['base']['ref']}",
        f"  URL:     {pr['html_url']}",
        f"  Created: {pr['created_at']}",
        f"  Updated: {pr['updated_at']}",
    ]
    if pr.get("body"):
        body_preview = pr["body"][:200]
        if len(pr["body"]) > 200:
            body_preview += "..."
        lines.append(f"  Body:    {body_preview}")
    return "\n".join(lines)


def fmt_comment(c: dict[str, Any]) -> str:
    lines = [
        f"Comment #{c['id']} by {c['user']['login']} ({c['created_at']})",
    ]
    if c.get("path"):
        line_info = f"  File: {c['path']}"
        if c.get("line"):
            line_info += f":{c['line']}"
        elif c.get("original_line"):
            line_info += f":{c['original_line']}"
        lines.append(line_info)
    if c.get("in_reply_to_id"):
        lines.append(f"  In reply to: #{c['in_reply_to_id']}")
    lines.append(f"  {c['body']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_create_pr(args: argparse.Namespace) -> None:
    url = f"{BASE_URL}/repos/{args.owner}/{args.repo}/pulls"
    data: dict[str, Any] = {
        "title": args.title,
        "head": args.head,
        "base": args.base,
    }
    if args.body:
        data["body"] = args.body
    if args.draft:
        data["draft"] = True

    pr = api_request(url, method="POST", data=data)
    print(fmt_pr(pr))


def cmd_update_pr(args: argparse.Namespace) -> None:
    url = f"{BASE_URL}/repos/{args.owner}/{args.repo}/pulls/{args.number}"
    data: dict[str, Any] = {}
    if args.title:
        data["title"] = args.title
    if args.body:
        data["body"] = args.body
    if args.state:
        data["state"] = args.state
    if args.base:
        data["base"] = args.base

    if not data:
        print("Error: No update fields specified.", file=sys.stderr)
        sys.exit(1)

    pr = api_request(url, method="PATCH", data=data)
    print(fmt_pr(pr))


def cmd_list_prs(args: argparse.Namespace) -> None:
    params = [
        f"state={args.state}",
        f"sort={args.sort}",
        f"direction={args.direction}",
        f"per_page={args.page_size}",
        f"page={args.page}",
    ]
    if args.head:
        # GitHub expects owner:branch for cross-fork, or just branch for same-repo
        params.append(f"head={args.head}")
    if args.base:
        params.append(f"base={args.base}")

    url = f"{BASE_URL}/repos/{args.owner}/{args.repo}/pulls?{'&'.join(params)}"
    prs = api_request(url)

    if not prs:
        print("No pull requests found.")
        return

    for pr in prs:
        print(fmt_pr(pr))
        print()


def cmd_get_pr(args: argparse.Namespace) -> None:
    url = f"{BASE_URL}/repos/{args.owner}/{args.repo}/pulls/{args.number}"
    pr = api_request(url)
    print(fmt_pr(pr))

    # Fetch files
    files_url = f"{url}/files?per_page=100"
    files = api_request(files_url)
    if files:
        print(f"\nFiles changed ({len(files)}):")
        for f in files:
            status = f["status"]
            additions = f.get("additions", 0)
            deletions = f.get("deletions", 0)
            print(f"  {status:10s} +{additions}/-{deletions}  {f['filename']}")


def cmd_comments(args: argparse.Namespace) -> None:
    # Issue comments (general PR comments)
    issue_url = f"{BASE_URL}/repos/{args.owner}/{args.repo}/issues/{args.number}/comments?per_page=100"
    issue_comments = api_request(issue_url)

    # Review comments (inline code comments)
    review_url = f"{BASE_URL}/repos/{args.owner}/{args.repo}/pulls/{args.number}/comments?per_page=100"
    review_comments = api_request(review_url)

    if not issue_comments and not review_comments:
        print("No comments found.")
        return

    if issue_comments:
        print("=== General Comments ===\n")
        for c in issue_comments:
            print(fmt_comment(c))
            print()

    if review_comments:
        print("=== Review Comments ===\n")
        for c in review_comments:
            print(fmt_comment(c))
            print()


def cmd_comment(args: argparse.Namespace) -> None:
    if args.path:
        # Review comment on a specific file/line
        url = f"{BASE_URL}/repos/{args.owner}/{args.repo}/pulls/{args.number}/comments"
        data: dict[str, Any] = {
            "body": args.text,
            "path": args.path,
            "commit_id": _get_pr_head_sha(args.owner, args.repo, args.number),
        }
        if args.line:
            data["line"] = args.line
            data["side"] = "RIGHT"
        else:
            data["subject_type"] = "file"
    else:
        # General issue comment
        url = f"{BASE_URL}/repos/{args.owner}/{args.repo}/issues/{args.number}/comments"
        data = {"body": args.text}

    comment = api_request(url, method="POST", data=data)
    print(fmt_comment(comment))


def cmd_review(args: argparse.Namespace) -> None:
    url = f"{BASE_URL}/repos/{args.owner}/{args.repo}/pulls/{args.number}/reviews"
    data: dict[str, Any] = {"event": args.event}
    if args.body:
        data["body"] = args.body

    review = api_request(url, method="POST", data=data)
    print(f"Review #{review['id']} submitted: {review['state']}")
    if review.get("body"):
        print(f"  {review['body']}")


def cmd_review_comment(args: argparse.Namespace) -> None:
    url = f"{BASE_URL}/repos/{args.owner}/{args.repo}/pulls/{args.number}/comments"
    data: dict[str, Any] = {
        "body": args.text,
        "path": args.path,
        "line": args.line,
        "side": args.side,
        "commit_id": _get_pr_head_sha(args.owner, args.repo, args.number),
    }

    comment = api_request(url, method="POST", data=data)
    print(fmt_comment(comment))


def cmd_reply(args: argparse.Namespace) -> None:
    url = (
        f"{BASE_URL}/repos/{args.owner}/{args.repo}/pulls/{args.number}"
        f"/comments/{args.comment_id}/replies"
    )
    data = {"body": args.text}
    comment = api_request(url, method="POST", data=data)
    print(fmt_comment(comment))


def cmd_resolve(args: argparse.Namespace) -> None:
    token = get_token()

    # Step 1: Get the node_id of the comment
    comment_url = (
        f"{BASE_URL}/repos/{args.owner}/{args.repo}/pulls/comments/{args.comment_id}"
    )
    comment = api_request(comment_url, token=token)
    node_id = comment["node_id"]

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
    result = graphql(query, {"nodeId": node_id})

    if "errors" in result:
        print(f"GraphQL error: {result['errors']}", file=sys.stderr)
        sys.exit(1)

    threads = (
        result.get("data", {})
        .get("node", {})
        .get("pullRequestReview", {})
        .get("pullRequest", {})
        .get("reviewThreads", {})
        .get("nodes", [])
    )

    thread_id = None
    for thread in threads:
        comments = thread.get("comments", {}).get("nodes", [])
        if comments and comments[0].get("databaseId") == args.comment_id:
            thread_id = thread["id"]
            break

    if not thread_id:
        print("Error: Could not find review thread for this comment.", file=sys.stderr)
        sys.exit(1)

    # Step 3: Resolve or unresolve
    if args.unresolve:
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

    result = graphql(mutation, {"threadId": thread_id})
    if "errors" in result:
        print(f"GraphQL error: {result['errors']}", file=sys.stderr)
        sys.exit(1)

    print(f"{action} thread for comment #{args.comment_id}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_pr_head_sha(owner: str, repo: str, number: int) -> str:
    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls/{number}"
    pr = api_request(url)
    return pr["head"]["sha"]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="github_cli",
        description="GitHub PR management CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # -- create-pr --
    p = sub.add_parser("create-pr", help="Create a pull request")
    p.add_argument("--owner", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--head", required=True, help="Source branch")
    p.add_argument("--base", required=True, help="Target branch")
    p.add_argument("--body", default=None)
    p.add_argument("--draft", action="store_true")
    p.set_defaults(func=cmd_create_pr)

    # -- update-pr --
    p = sub.add_parser("update-pr", help="Update a pull request")
    p.add_argument("--owner", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--number", required=True, type=int)
    p.add_argument("--title", default=None)
    p.add_argument("--body", default=None)
    p.add_argument("--state", choices=["open", "closed"], default=None)
    p.add_argument("--base", default=None)
    p.set_defaults(func=cmd_update_pr)

    # -- list-prs --
    p = sub.add_parser("list-prs", help="List pull requests")
    p.add_argument("--owner", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--state", default="open", choices=["open", "closed", "all"])
    p.add_argument("--sort", default="updated", choices=["created", "updated", "popularity", "long-running"])
    p.add_argument("--direction", default="desc", choices=["asc", "desc"])
    p.add_argument("--head", default=None)
    p.add_argument("--base", default=None)
    p.add_argument("--page", default=1, type=int)
    p.add_argument("--page-size", default=20, type=int)
    p.set_defaults(func=cmd_list_prs)

    # -- get-pr --
    p = sub.add_parser("get-pr", help="Get PR details")
    p.add_argument("--owner", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--number", required=True, type=int)
    p.set_defaults(func=cmd_get_pr)

    # -- comments --
    p = sub.add_parser("comments", help="Get PR comments")
    p.add_argument("--owner", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--number", required=True, type=int)
    p.set_defaults(func=cmd_comments)

    # -- comment --
    p = sub.add_parser("comment", help="Add a PR comment")
    p.add_argument("--owner", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--number", required=True, type=int)
    p.add_argument("text", help="Comment body")
    p.add_argument("--path", default=None, help="File path for inline comment")
    p.add_argument("--line", default=None, type=int, help="Line number for inline comment")
    p.set_defaults(func=cmd_comment)

    # -- review --
    p = sub.add_parser("review", help="Create a PR review")
    p.add_argument("--owner", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--number", required=True, type=int)
    p.add_argument("--event", required=True, choices=["APPROVE", "REQUEST_CHANGES", "COMMENT"])
    p.add_argument("--body", default=None)
    p.set_defaults(func=cmd_review)

    # -- review-comment --
    p = sub.add_parser("review-comment", help="Create inline review comment")
    p.add_argument("--owner", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--number", required=True, type=int)
    p.add_argument("--path", required=True, help="File path")
    p.add_argument("--line", required=True, type=int, help="Line number")
    p.add_argument("text", help="Comment body")
    p.add_argument("--side", default="RIGHT", choices=["RIGHT", "LEFT"])
    p.set_defaults(func=cmd_review_comment)

    # -- reply --
    p = sub.add_parser("reply", help="Reply to a review comment")
    p.add_argument("--owner", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--number", required=True, type=int)
    p.add_argument("--comment-id", required=True, type=int)
    p.add_argument("text", help="Reply body")
    p.set_defaults(func=cmd_reply)

    # -- resolve --
    p = sub.add_parser("resolve", help="Resolve/unresolve a review thread")
    p.add_argument("--owner", required=True)
    p.add_argument("--repo", required=True)
    p.add_argument("--number", required=True, type=int)
    p.add_argument("--comment-id", required=True, type=int)
    p.add_argument("--unresolve", action="store_true")
    p.set_defaults(func=cmd_resolve)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
