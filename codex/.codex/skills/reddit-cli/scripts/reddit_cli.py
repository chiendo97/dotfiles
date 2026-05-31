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
import sys
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from itertools import islice
from typing import Literal, TextIO, TypedDict

import praw
from dotenv import load_dotenv
from praw.models import MoreComments

type JsonValue = (
    None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]
)
type SearchPostSort = Literal["relevance", "hot", "top", "new", "comments"]
type SearchSyntax = Literal["cloudsearch", "lucene", "plain"]
type SearchTime = Literal["all", "year", "month", "week", "day", "hour"]


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
        load_dotenv()
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
            raise RuntimeError(
                f"Missing required environment variable(s): {missing_names}"
            )

        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )

    @classmethod
    def get_instance(cls) -> RedditClient:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


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


def cmd_status(_args: argparse.Namespace) -> dict[str, JsonValue]:
    client = RedditClient.get_instance()
    subreddit = client.reddit.subreddit("python")
    first = next(subreddit.hot(limit=1))
    return {
        "ok": True,
        "read_only": client.reddit.read_only,
        "probe": {
            "subreddit": subreddit.display_name,
            "post_id": first.id,
        },
    }


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
