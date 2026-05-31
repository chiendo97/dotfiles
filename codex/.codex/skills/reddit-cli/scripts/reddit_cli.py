#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "praw>=7.8.1",
#   "python-dotenv>=1.0.1",
# ]
# ///
from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from itertools import islice
from typing import Literal, TextIO, TypedDict
from urllib.parse import parse_qs, urlparse

import praw
from dotenv import load_dotenv
from praw.models import Comment, MoreComments, Submission

type JsonValue = (
    None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]
)
type SearchPostSort = Literal["relevance", "hot", "top", "new", "comments"]
type SearchSyntax = Literal["cloudsearch", "lucene", "plain"]
type SearchTime = Literal["all", "year", "month", "week", "day", "hour"]
type UpvotedItemType = Literal["all", "posts", "comments"]

DEFAULT_OAUTH_SCOPES = ["identity", "read", "history"]
DEFAULT_REDIRECT_URI = "http://localhost:8080"
CONFIG_ENV_FILE = os.path.expanduser("~/.config/reddit-cli/.env")


class SearchPostsParams(TypedDict):
    subreddit_name: str
    query: str
    sort: SearchPostSort
    syntax: SearchSyntax
    time_filter: SearchTime


class SearchSubredditsParams(TypedDict):
    type: Literal["name", "description"]
    query: str
    include_nsfw: bool
    exact_match: bool
    include_full_description: bool


class RedditClient:
    _instance: RedditClient | None = None

    def __init__(self) -> None:
        load_env()
        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        refresh_token = os.getenv("REDDIT_REFRESH_TOKEN")
        redirect_uri = os.getenv("REDDIT_REDIRECT_URI", DEFAULT_REDIRECT_URI)
        user_agent = os.getenv("REDDIT_USER_AGENT", "reddit-cli-praw/0.1")

        missing = [
            name
            for name, value in {
                "REDDIT_CLIENT_ID": client_id,
                "REDDIT_CLIENT_SECRET": client_secret,
            }.items()
            if not value
        ]
        if missing:
            missing_names = ", ".join(missing)
            raise RuntimeError(
                f"Missing required environment variable(s): {missing_names}"
            )

        kwargs: dict[str, str] = {
            "client_id": client_id,
            "client_secret": client_secret,
            "user_agent": user_agent,
            "redirect_uri": redirect_uri,
        }
        if refresh_token:
            kwargs["refresh_token"] = refresh_token
            self.auth_mode = "refresh_token"
        else:
            self.auth_mode = "application_only"

        self.reddit = praw.Reddit(**kwargs)

    @classmethod
    def get_instance(cls) -> RedditClient:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def load_env() -> None:
    load_dotenv()
    load_dotenv(CONFIG_ENV_FILE)


def format_utc_timestamp(timestamp: float, fmt: str = "%Y-%m-%d") -> str:
    return datetime.fromtimestamp(timestamp, UTC).strftime(fmt)


def _emit(value: JsonValue, *, compact: bool, stream: TextIO | None = None) -> None:
    target = stream or sys.stdout
    kwargs: dict[str, bool | int] = {"ensure_ascii": False}
    if not compact:
        kwargs["indent"] = 2
    print(json.dumps(value, **kwargs), file=target)


def _limit(items: Sequence[JsonValue], limit: int | None) -> list[JsonValue]:
    if limit is None:
        return list(items)
    return list(islice(items, limit))


def _require_configured_app(redirect_uri: str) -> praw.Reddit:
    load_env()
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT", "reddit-cli-praw/0.1")
    missing = [
        name
        for name, value in {
            "REDDIT_CLIENT_ID": client_id,
            "REDDIT_CLIENT_SECRET": client_secret,
        }.items()
        if not value
    ]
    if missing:
        missing_names = ", ".join(missing)
        raise RuntimeError(f"Missing required environment variable(s): {missing_names}")
    return praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        user_agent=user_agent,
    )


def _extract_code_and_state(value: str) -> tuple[str, str | None]:
    parsed = urlparse(value)
    query = parse_qs(parsed.query)

    errors = query.get("error")
    if errors:
        raise RuntimeError(f"Reddit OAuth returned error: {errors[0]}")

    codes = query.get("code")
    if codes:
        return codes[0], query.get("state", [None])[0]

    return value, None


def _save_refresh_token(refresh_token: str) -> str:
    config_dir = os.path.dirname(CONFIG_ENV_FILE)
    os.makedirs(config_dir, mode=0o700, exist_ok=True)
    old_umask = os.umask(0o177)
    try:
        with open(CONFIG_ENV_FILE, "w", encoding="utf-8") as f:
            f.write(f"REDDIT_REFRESH_TOKEN={json.dumps(refresh_token)}\n")
        os.chmod(CONFIG_ENV_FILE, 0o600)
    finally:
        os.umask(old_umask)
    return CONFIG_ENV_FILE


def _comment_to_dict(comment: object) -> dict[str, JsonValue] | None:
    if isinstance(comment, MoreComments):
        return None

    replies = [
        result
        for reply in comment.replies
        if (result := _comment_to_dict(reply)) is not None
    ]
    return {
        "id": comment.id,
        "body": comment.body,
        "author": None if comment.author is None else comment.author.name,
        "created_utc": format_utc_timestamp(comment.created_utc),
        "is_submitter": comment.is_submitter,
        "score": comment.score,
        "replies": replies,
    }


def _submission_to_dict(submission: Submission) -> dict[str, JsonValue]:
    return {
        "kind": "submission",
        "id": submission.id,
        "title": submission.title,
        "url": submission.url,
        "author": None if submission.author is None else submission.author.name,
        "subreddit": submission.subreddit.display_name,
        "score": submission.score,
        "num_comments": submission.num_comments,
        "selftext": submission.selftext,
        "created_utc": format_utc_timestamp(submission.created_utc),
        "permalink": f"https://www.reddit.com{submission.permalink}",
    }


def _flat_comment_to_dict(comment: Comment) -> dict[str, JsonValue]:
    submission_id = comment.link_id.removeprefix("t3_")
    return {
        "kind": "comment",
        "id": comment.id,
        "body": comment.body,
        "author": None if comment.author is None else comment.author.name,
        "subreddit": comment.subreddit.display_name,
        "submission_id": submission_id,
        "score": comment.score,
        "created_utc": format_utc_timestamp(comment.created_utc),
        "permalink": f"https://www.reddit.com{comment.permalink}",
    }


def _history_item_to_dict(item: object) -> dict[str, JsonValue] | None:
    if isinstance(item, Submission):
        return _submission_to_dict(item)
    if isinstance(item, Comment):
        return _flat_comment_to_dict(item)
    return None


def _matches_item_type(item: dict[str, JsonValue], item_type: UpvotedItemType) -> bool:
    if item_type == "all":
        return True
    if item_type == "posts":
        return item["kind"] == "submission"
    return item["kind"] == "comment"


def get_submission(submission_id: str) -> dict[str, JsonValue]:
    client = RedditClient.get_instance()
    submission = client.reddit.submission(submission_id)
    return {
        "title": submission.title,
        "url": submission.url,
        "author": None if submission.author is None else submission.author.name,
        "subreddit": submission.subreddit.display_name,
        "score": submission.score,
        "num_comments": submission.num_comments,
        "selftext": submission.selftext,
        "created_utc": format_utc_timestamp(submission.created_utc),
    }


def get_subreddit(subreddit_name: str) -> dict[str, JsonValue]:
    client = RedditClient.get_instance()
    subreddit = client.reddit.subreddit(subreddit_name)
    return {
        "display_name": subreddit.display_name,
        "title": subreddit.title,
        "description": subreddit.description,
        "public_description": subreddit.public_description,
        "subscribers": subreddit.subscribers,
        "created_utc": subreddit.created_utc,
        "over18": subreddit.over18,
        "url": subreddit.url,
    }


def get_comments_by_submission(
    submission_id: str,
    *,
    replace_more: bool = True,
) -> list[JsonValue]:
    client = RedditClient.get_instance()
    submission = client.reddit.submission(submission_id)
    if replace_more:
        submission.comments.replace_more()
    return [
        result
        for comment in submission.comments.list()
        if (result := _comment_to_dict(comment)) is not None
    ]


def get_comment_by_id(comment_id: str) -> dict[str, JsonValue]:
    client = RedditClient.get_instance()
    result = _comment_to_dict(client.reddit.comment(comment_id))
    if result is None:
        raise RuntimeError(f"No comment found for id: {comment_id}")
    return result


def search_posts(params: SearchPostsParams) -> list[JsonValue]:
    client = RedditClient.get_instance()
    subreddit = client.reddit.subreddit(params["subreddit_name"])
    posts = subreddit.search(
        query=params["query"],
        sort=params["sort"],
        syntax=params["syntax"],
        time_filter=params["time_filter"],
    )
    return [
        {
            "id": post.id,
            "title": post.title,
            "url": post.url,
            "score": post.score,
            "num_comments": post.num_comments,
            "created_utc": format_utc_timestamp(post.created_utc),
        }
        for post in posts
    ]


def search_subreddits(params: SearchSubredditsParams) -> list[JsonValue]:
    client = RedditClient.get_instance()
    if params["type"] == "name":
        subreddits = client.reddit.subreddits.search_by_name(
            params["query"],
            exact=params["exact_match"],
            include_nsfw=params["include_nsfw"],
        )
    else:
        subreddits = client.reddit.subreddits.search(params["query"])

    return [
        {
            "name": subreddit.display_name,
            "public_description": subreddit.public_description,
            "description": (
                subreddit.description
                if (
                    params["type"] == "description"
                    and params["include_full_description"]
                )
                else None
            ),
            "url": subreddit.url,
            "subscribers": subreddit.subscribers,
            "created_utc": format_utc_timestamp(subreddit.created_utc),
        }
        for subreddit in subreddits
    ]


def get_my_upvoted(
    *,
    item_type: UpvotedItemType,
    limit: int,
    scan_limit: int | None,
) -> dict[str, JsonValue]:
    client = RedditClient.get_instance()
    if client.auth_mode != "refresh_token":
        raise RuntimeError(
            "my-upvoted requires REDDIT_REFRESH_TOKEN. Run auth-url and auth-token "
            "first, then export REDDIT_REFRESH_TOKEN."
        )

    me = client.reddit.user.me()
    if me is None:
        raise RuntimeError("Could not resolve authenticated Reddit user")

    effective_scan_limit = scan_limit
    if effective_scan_limit is None:
        effective_scan_limit = limit if item_type == "all" else max(limit * 3, limit)

    items: list[JsonValue] = []
    for raw_item in me.upvoted(limit=effective_scan_limit):
        item = _history_item_to_dict(raw_item)
        if item is None or not _matches_item_type(item, item_type):
            continue
        items.append(item)
        if len(items) >= limit:
            break

    return {
        "username": me.name,
        "item_type": item_type,
        "limit": limit,
        "scan_limit": effective_scan_limit,
        "items": items,
    }


def cmd_auth_url(args: argparse.Namespace) -> dict[str, JsonValue]:
    scopes = args.scope or DEFAULT_OAUTH_SCOPES
    state = args.state or secrets.token_urlsafe(24)
    reddit = _require_configured_app(args.redirect_uri)
    return {
        "url": reddit.auth.url(
            duration="permanent",
            scopes=scopes,
            state=state,
        ),
        "state": state,
        "scopes": scopes,
        "redirect_uri": args.redirect_uri,
    }


def cmd_auth_token(args: argparse.Namespace) -> dict[str, JsonValue]:
    code, state = _extract_code_and_state(args.code_or_url)
    if args.state is not None and state != args.state:
        raise RuntimeError(
            f"OAuth state mismatch: expected {args.state!r}, received {state!r}"
        )

    reddit = _require_configured_app(args.redirect_uri)
    refresh_token = reddit.auth.authorize(code)
    if refresh_token is None:
        raise RuntimeError("Reddit did not return a refresh token")

    result: dict[str, JsonValue] = {
        "state": state,
        "redirect_uri": args.redirect_uri,
    }
    if args.save:
        result["saved"] = True
        result["path"] = _save_refresh_token(refresh_token)
        result["env_var"] = "REDDIT_REFRESH_TOKEN"
        if args.show_token:
            result["refresh_token"] = refresh_token
    else:
        result["refresh_token"] = refresh_token
        result["env"] = f"export REDDIT_REFRESH_TOKEN={json.dumps(refresh_token)}"
    return result


def cmd_status(_args: argparse.Namespace) -> dict[str, JsonValue]:
    client = RedditClient.get_instance()
    subreddit = client.reddit.subreddit("python")
    first = next(subreddit.hot(limit=1))
    result: dict[str, JsonValue] = {
        "ok": True,
        "auth_mode": client.auth_mode,
        "read_only": client.reddit.read_only,
        "probe": {
            "subreddit": subreddit.display_name,
            "post_id": first.id,
        },
    }
    if client.auth_mode == "refresh_token":
        me = client.reddit.user.me()
        result["username"] = None if me is None else me.name
    return result


def cmd_get_subreddit(args: argparse.Namespace) -> dict[str, JsonValue]:
    return get_subreddit(args.name)


def cmd_get_submission(args: argparse.Namespace) -> dict[str, JsonValue]:
    return get_submission(args.id)


def cmd_get_comment(args: argparse.Namespace) -> dict[str, JsonValue]:
    return get_comment_by_id(args.id)


def cmd_get_comments(args: argparse.Namespace) -> list[JsonValue]:
    results = get_comments_by_submission(
        args.submission_id,
        replace_more=args.replace_more,
    )
    return _limit(results, args.limit)


def cmd_search_posts(args: argparse.Namespace) -> list[JsonValue]:
    params: SearchPostsParams = {
        "subreddit_name": args.subreddit,
        "query": args.query,
        "sort": args.sort,
        "syntax": args.syntax,
        "time_filter": args.time,
    }
    return _limit(search_posts(params), args.limit)


def cmd_search_subreddits(args: argparse.Namespace) -> list[JsonValue]:
    params: SearchSubredditsParams = {
        "type": args.by,
        "query": args.query,
        "include_nsfw": args.include_nsfw,
        "exact_match": args.exact_match,
        "include_full_description": args.include_full_description,
    }
    return _limit(search_subreddits(params), args.limit)


def cmd_my_upvoted(args: argparse.Namespace) -> dict[str, JsonValue]:
    return get_my_upvoted(
        item_type=args.item_type,
        limit=args.limit,
        scan_limit=args.scan_limit,
    )


def _add_compact_flag(parser: argparse.ArgumentParser, *, hidden: bool = False) -> None:
    help_text = argparse.SUPPRESS if hidden else "emit compact JSON"
    parser.add_argument("--compact", action="store_true", help=help_text)


def _add_handler(
    parser: argparse.ArgumentParser,
    handler: Callable[[argparse.Namespace], JsonValue],
) -> None:
    _add_compact_flag(parser, hidden=True)
    parser.set_defaults(handler=handler)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reddit-cli",
        description="Read-only Reddit CLI backed by PRAW.",
    )
    _add_compact_flag(parser)
    subparsers = parser.add_subparsers(dest="command", required=True)

    auth_url = subparsers.add_parser(
        "auth-url",
        help="print a browser OAuth approval URL for a refresh token",
    )
    auth_url.add_argument(
        "--redirect-uri",
        default=os.getenv("REDDIT_REDIRECT_URI", DEFAULT_REDIRECT_URI),
        help="redirect URI registered on the Reddit app",
    )
    auth_url.add_argument(
        "--scope",
        action="append",
        choices=("identity", "read", "history"),
        help="OAuth scope to request; repeat for multiple scopes",
    )
    auth_url.add_argument("--state", default=None, help="optional OAuth state value")
    _add_handler(auth_url, cmd_auth_url)

    auth_token = subparsers.add_parser(
        "auth-token",
        help="exchange a pasted redirect URL or code for a refresh token",
    )
    auth_token.add_argument("code_or_url")
    auth_token.add_argument(
        "--redirect-uri",
        default=os.getenv("REDDIT_REDIRECT_URI", DEFAULT_REDIRECT_URI),
        help="redirect URI registered on the Reddit app",
    )
    auth_token.add_argument("--state", default=None, help="expected OAuth state")
    auth_token.add_argument(
        "--save",
        action="store_true",
        help=f"save refresh token to {CONFIG_ENV_FILE}",
    )
    auth_token.add_argument(
        "--show-token",
        action="store_true",
        help="print token even when --save is used",
    )
    _add_handler(auth_token, cmd_auth_token)

    status = subparsers.add_parser(
        "status",
        help="validate credentials with a read probe",
    )
    _add_handler(status, cmd_status)

    get_subreddit_parser = subparsers.add_parser(
        "get-subreddit",
        help="get subreddit details",
    )
    get_subreddit_parser.add_argument("name")
    _add_handler(get_subreddit_parser, cmd_get_subreddit)

    get_submission_parser = subparsers.add_parser(
        "get-submission",
        help="get submission details",
    )
    get_submission_parser.add_argument("id")
    _add_handler(get_submission_parser, cmd_get_submission)

    get_comment_parser = subparsers.add_parser(
        "get-comment",
        help="get one comment by id",
    )
    get_comment_parser.add_argument("id")
    _add_handler(get_comment_parser, cmd_get_comment)

    get_comments_parser = subparsers.add_parser(
        "get-comments",
        help="get comments for a submission",
    )
    get_comments_parser.add_argument("submission_id")
    get_comments_parser.add_argument("--limit", type=int, default=None)
    get_comments_parser.add_argument(
        "--replace-more",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="expand Reddit MoreComments placeholders",
    )
    _add_handler(get_comments_parser, cmd_get_comments)

    search_posts_parser = subparsers.add_parser(
        "search-posts",
        help="search posts in a subreddit",
    )
    search_posts_parser.add_argument("subreddit")
    search_posts_parser.add_argument("query")
    search_posts_parser.add_argument("--limit", type=int, default=None)
    search_posts_parser.add_argument(
        "--sort",
        choices=("relevance", "hot", "top", "new", "comments"),
        default="relevance",
    )
    search_posts_parser.add_argument(
        "--syntax",
        choices=("cloudsearch", "lucene", "plain"),
        default="lucene",
    )
    search_posts_parser.add_argument(
        "--time",
        choices=("all", "year", "month", "week", "day", "hour"),
        default="all",
    )
    _add_handler(search_posts_parser, cmd_search_posts)

    search_subreddits_parser = subparsers.add_parser(
        "search-subreddits",
        help="search subreddits by name or description",
    )
    search_subreddits_parser.add_argument("query")
    search_subreddits_parser.add_argument("--limit", type=int, default=None)
    search_subreddits_parser.add_argument(
        "--by",
        choices=("name", "description"),
        default="name",
    )
    search_subreddits_parser.add_argument("--include-nsfw", action="store_true")
    search_subreddits_parser.add_argument("--exact-match", action="store_true")
    search_subreddits_parser.add_argument(
        "--include-full-description",
        action="store_true",
    )
    _add_handler(search_subreddits_parser, cmd_search_subreddits)

    my_upvoted_parser = subparsers.add_parser(
        "my-upvoted",
        help="list upvoted items for the authenticated user",
    )
    my_upvoted_parser.add_argument("--limit", type=int, default=25)
    my_upvoted_parser.add_argument(
        "--scan-limit",
        type=int,
        default=None,
        help="history items to scan before item-type filtering",
    )
    my_upvoted_parser.add_argument(
        "--item-type",
        choices=("all", "posts", "comments"),
        default="posts",
        help="which upvoted item type to return",
    )
    _add_handler(my_upvoted_parser, cmd_my_upvoted)

    return parser


def run(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler: Callable[[argparse.Namespace], JsonValue] = args.handler

    try:
        result = handler(args)
    except Exception as exc:
        _emit(
            {"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}},
            compact=args.compact,
            stream=sys.stderr,
        )
        return 1

    _emit(result, compact=args.compact)
    return 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
