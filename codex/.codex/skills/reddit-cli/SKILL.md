---
name: reddit-cli
description: "Use the local reddit-cli wrapper for Reddit read workflows: resolving Reddit share links, fetching submissions and comments, searching posts or subreddits, and summarizing Reddit discussions. Trigger when the user asks to inspect, summarize, research, search, or quote Reddit content using the local CLI rather than MCP/browser scraping."
---

# Reddit CLI

Use the bundled single-file Reddit CLI for read-only Reddit operations:

```bash
uv run "${CODEX_HOME:-$HOME/.codex}/skills/reddit-cli/scripts/reddit_cli.py" ...
```

The script is a PEP 723 `uv` script backed by PRAW. It reads app credentials from `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET`; `REDDIT_USER_AGENT` is optional. It uses app-only read mode by default, and switches to user OAuth when `REDDIT_REFRESH_TOKEN` is present in the environment or saved in `~/.config/reddit-cli/.env`. An editable package entrypoint named `reddit-cli` may also exist, but prefer the bundled script because the skill carries it alongside these instructions and the script carries its dependencies inline.

## First Checks

Verify the tool and credentials without exposing secrets:

```bash
test -f "${CODEX_HOME:-$HOME/.codex}/skills/reddit-cli/scripts/reddit_cli.py"
uv run "${CODEX_HOME:-$HOME/.codex}/skills/reddit-cli/scripts/reddit_cli.py" status --compact
```

If status fails with missing env vars, report that Reddit API credentials are not available. Do not print secret values. If status succeeds, continue with the requested Reddit task.

## Headless User OAuth

Use this flow when the user asks for account-private history such as upvoted items. The server can be headless; browser approval can happen on any machine.

Generate an approval URL:

```bash
uv run "${CODEX_HOME:-$HOME/.codex}/skills/reddit-cli/scripts/reddit_cli.py" auth-url --compact
```

Open the printed `url` in a browser. After approving, the browser may show a localhost connection error. That is fine: copy the full address-bar URL, then exchange it on the server:

```bash
uv run "${CODEX_HOME:-$HOME/.codex}/skills/reddit-cli/scripts/reddit_cli.py" auth-token '<redirected-url>' --state '<state-from-auth-url>' --save --compact
```

With `--save`, the refresh token is written to `~/.config/reddit-cli/.env` with private file permissions and is not printed. Without `--save`, the `refresh_token` in the output is a secret; do not print it back to the user unless the user explicitly asks. To set it manually:

```bash
export REDDIT_REFRESH_TOKEN='<refresh-token>'
```

If the Reddit app uses a redirect URI other than `http://localhost:8080`, set `REDDIT_REDIRECT_URI` or pass `--redirect-uri` to both `auth-url` and `auth-token`.

Fetch upvoted posts after `REDDIT_REFRESH_TOKEN` is set:

```bash
uv run "${CODEX_HOME:-$HOME/.codex}/skills/reddit-cli/scripts/reddit_cli.py" my-upvoted --limit 25 --item-type posts --compact
```

Use `--item-type all|posts|comments`. For filtered results, increase `--scan-limit` if the command returns fewer items than requested because the Reddit history contains mixed posts and comments.

## Summarize a Reddit Link

For `reddit.com/r/.../s/...` share links, resolve the canonical URL first:

```bash
curl -Ls -o /dev/null -w '%{url_effective}\n' '<url>'
```

Extract the submission id from `/comments/<id>/...`, then fetch the post and a bounded comment set:

```bash
uv run "${CODEX_HOME:-$HOME/.codex}/skills/reddit-cli/scripts/reddit_cli.py" get-submission <id> --compact
uv run "${CODEX_HOME:-$HOME/.codex}/skills/reddit-cli/scripts/reddit_cli.py" get-comments <id> --no-replace-more --limit 25 --compact
```

Summarize from the CLI JSON:

- Include the resolved post path or id.
- State the OP question or claim.
- Identify the main consensus and meaningful disagreements.
- Highlight concrete links, libraries, tools, commands, or next steps mentioned in comments.
- Mention limitations, such as only summarizing the fetched comment sample when not all comments are loaded.
- Deduplicate comments by `id` when aggregating because flattened comment output can repeat replies that also appear nested under parents.

Use `--replace-more` only when the user needs a deeper thread read; it can be slower and produce much larger output.

## Search Reddit

Search posts in a subreddit:

```bash
uv run "${CODEX_HOME:-$HOME/.codex}/skills/reddit-cli/scripts/reddit_cli.py" search-posts <subreddit> '<query>' --sort relevance --time all --limit 10 --compact
```

Search subreddits:

```bash
uv run "${CODEX_HOME:-$HOME/.codex}/skills/reddit-cli/scripts/reddit_cli.py" search-subreddits '<query>' --limit 10 --compact
uv run "${CODEX_HOME:-$HOME/.codex}/skills/reddit-cli/scripts/reddit_cli.py" search-subreddits '<query>' --by description --limit 10 --compact
```

For research tasks, prefer a short search first, then fetch individual submissions and comments only for the most relevant posts.

## Fetch Specific Objects

Use these commands for direct lookups:

```bash
uv run "${CODEX_HOME:-$HOME/.codex}/skills/reddit-cli/scripts/reddit_cli.py" get-subreddit <name> --compact
uv run "${CODEX_HOME:-$HOME/.codex}/skills/reddit-cli/scripts/reddit_cli.py" get-submission <id> --compact
uv run "${CODEX_HOME:-$HOME/.codex}/skills/reddit-cli/scripts/reddit_cli.py" get-comment <id> --compact
uv run "${CODEX_HOME:-$HOME/.codex}/skills/reddit-cli/scripts/reddit_cli.py" get-comments <submission_id> --no-replace-more --limit 25 --compact
```

All successful commands emit JSON to stdout. Errors emit structured JSON to stderr and exit non-zero.

## Boundaries

- Treat the tool as read-only. It does not post, vote, save, subscribe, or access account-private feeds.
- Prefer this CLI over generic web scraping for Reddit because it uses the configured API credentials and returns structured JSON.
- Do not browse Reddit in a browser unless the CLI cannot resolve or fetch the content.
