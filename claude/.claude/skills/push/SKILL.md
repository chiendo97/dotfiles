---
name: push
description: |
  Go from uncommitted changes to a GitHub PR or GitLab MR with a linked Notion ticket in one step.
  Checks git status, creates a branch/worktree if on main/master, commits changes,
  finds or creates a Notion ticket, pushes, and opens a PR/MR following team conventions.
  Also handles post-push tasks like attaching a Notion ticket to an existing PR/MR.
  Use whenever the user says "push", "ship", "ship it", "create PR", "create MR",
  "open PR", "open MR", "submit", "push changes", "/push", "wrap up", "send this out",
  or when the user has finished coding and wants to get their changes into a PR/MR.
  Even casual phrases like "let's get this merged" or "I'm done, push it" should trigger this.
  Also triggers for "create ticket and attach to MR", "link notion ticket", or similar.
---

# Push

One-command workflow: uncommitted changes -> commit -> Notion ticket -> PR/MR.

Also handles partial flows: already pushed but need a ticket, existing MR needs a ticket link, etc.

## Step 1: Assess the Situation

Run these in parallel via Bash:

```bash
git status
git branch --show-current
git remote get-url origin
git log --oneline -5
git remote show origin | grep 'HEAD branch'
```

Extract:
- **current_branch**: the branch you're on
- **has_changes**: whether there are staged, unstaged, or untracked changes
- **remote_url**: to derive the forge type and repo path (see Step 1b)
- **default_branch**: `main` or `master` (from `HEAD branch`)

### Step 1b: Detect Forge Type

Parse the remote URL to determine GitHub vs GitLab:

| Remote URL pattern | Forge | CLI tool |
|---|---|---|
| `github.com` in URL | GitHub | `gh` |
| Anything else (e.g. `git.urieljsc.com`, self-hosted GitLab) | GitLab | `glab` |

Extract `owner` and `repo` from the URL:
- SSH: `git@<host>:<owner>/<repo>.git` -> owner, repo
- HTTPS: `https://<host>/<owner>/<repo>.git` -> owner, repo

Store `forge_type` (`github` or `gitlab`) and `forge_cli` (`gh` or `glab`) for later steps.

### Step 1c: Decide Flow

Not every push needs every step. Decide what to do based on the current state:

| State | Action |
|---|---|
| Has uncommitted changes | Full flow: commit -> lint -> ticket -> push -> PR/MR |
| Clean tree, not pushed yet | Partial: lint -> ticket -> push -> PR/MR |
| Clean tree, already pushed, no PR/MR | Partial: ticket -> create PR/MR |
| Clean tree, already pushed, PR/MR exists | Partial: ticket -> update PR/MR description |

The user's arguments (e.g. "create new notion ticket") also guide which steps to run. If the user specifically asks to create/attach a ticket, always do the Notion step even if the tree is clean.

## Step 2: Branch Strategy

### Already on a feature branch

If `current_branch` is NOT `main`/`master`, skip to Step 3. The branch is ready.

### On main/master with changes -- create a worktree

The user is working directly on the default branch. Create a new branch in an isolated worktree under `.worktrees/` in the current project root so main/master stays clean and reusable for future worktrees.

1. **Ask the user** (via AskUserQuestion) for:
   - **Type**: `feat`, `fix`, `refactor`, `chore`, or `docs`
   - **Short description**: kebab-case, e.g. `sales-v2-filter-by`

   If the user invoked the skill with arguments (e.g. `/push fix: sales filter`), parse the type and description from those arguments instead of asking.

2. **Author prefix**: Use `$USER` environment variable.

3. **Construct the branch name**: `$USER/<type>/<description>` (e.g. `cle/fix/sales-v2-filter-by`)

4. **Create worktree with the changes**:
   ```bash
   git stash --include-untracked
   mkdir -p .worktrees
   git worktree add .worktrees/<description> -b $USER/<type>/<description>
   cd .worktrees/<description>
   git stash pop
   ```

5. **Switch the session** to the new worktree directory. All remaining steps run from `.worktrees/<description>`.

6. Tell the user: "Created worktree at `.worktrees/<description>` on branch `<branch>`. After this session, start new sessions from that directory."

## Step 3: Commit

Skip if working tree is clean (no changes to commit).

1. Run `git diff --stat` and `git diff` to understand the changes.
2. Stage relevant files explicitly (`git add <file> ...`). Avoid `git add -A` -- never stage `.env`, credentials, or secrets.
3. Generate a concise commit message:
   - Use conventional prefix: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`
   - Focus on the "why", not the "what"
   - Keep the first line under 72 characters
4. Commit:
   ```bash
   git commit -m "$(cat <<'EOF'
   type: concise description of changes

   Co-Authored-By: Claude <noreply@anthropic.com>
   EOF
   )"
   ```

If pre-commit hooks fail, fix the issues and create a NEW commit -- never amend.

## Step 4: Lint

Run `make lint` to catch issues before pushing. If lint fails:

1. Read the error output and fix the issues (formatting, type errors, import order, etc.).
2. Stage the fixes and create a NEW commit (e.g. `fix: lint errors`).
3. Re-run `make lint` to confirm it passes.

Do not proceed to Step 5 until `make lint` passes.

## Step 5: Notion Ticket

Find or create a Notion ticket in the **genbook-global** project so the PR/MR has a ticket reference.

The Notion CLI lives at: `~/.claude/skills/notion/notion_cli.py`
Run it with: `uv run <path>/notion_cli.py <command> [options]`

### Search first

```bash
uv run ~/.claude/skills/notion/notion_cli.py search \
  --project genbook-global \
  --assignee $USER \
  --status "In Progress"
```

Scan the results for a ticket whose title relates to the changes being committed. Consider:
- Keywords from the branch name or commit message
- The domain area being changed (e.g., "sales", "orders", "pipeline")

### Reuse or create

- **If a matching ticket exists**: Confirm with the user -- "Found ticket `XXXX`: '_title_'. Use this?"
- **If no match or user declines**: Create a new ticket:

```bash
uv run ~/.claude/skills/notion/notion_cli.py create \
  --project genbook-global \
  --title "Short description matching the PR/MR" \
  --description "Summary of the changes" \
  --priority Medium \
  --assignee $USER \
  --status "In progress"
```

### Get the ticket ID

The `create` command outputs:
```
Created: <title>
Ticket: GGA-167
ID: <uuid>
URL: https://www.notion.so/<slug>-<page-id>
```

Extract the ticket ID (e.g. `GGA-167`) and the full Notion URL for Step 6.

## Step 6: Push and Create/Update PR or MR

### Check for existing PR/MR

**GitHub:**
```bash
gh pr list --head <branch-name> --json number,url --jq '.[0]'
```

**GitLab:**
```bash
glab mr list --source-branch <branch-name>
```

### If PR/MR already exists -- update it

Push any new commits, then update the title and description to include the ticket:

**GitLab:**
```bash
git push
glab mr update <mr-number> \
  --title "[<ticket-id>] type: short description" \
  --description "$(cat <<'EOF'
## Summary

**Ticket:** [<ticket-id>](<notion-url>)

- Bullet point describing what changed and why

## Test plan

- [x] `make lint` passes
- [ ] `make test` passes

Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

**GitHub:**
```bash
git push
gh pr edit <pr-number> \
  --title "[<ticket-id>] type: short description" \
  --body "$(cat <<'EOF'
## Summary

**Ticket:** [<ticket-id>](<notion-url>)

- Bullet point describing what changed and why

## Test plan

- [x] `make lint` passes
- [ ] `make test` passes

Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

Return the PR/MR URL to the user. Done.

### If no PR/MR exists -- create one

Push first:
```bash
git push -u origin <branch-name>
```

Then create:

**GitLab:**
```bash
glab mr create --fill \
  --title "[<ticket-id>] type: short description" \
  --description "$(cat <<'EOF'
## Summary

**Ticket:** [<ticket-id>](<notion-url>)

- Bullet point describing what changed and why

## Test plan

- [x] `make lint` passes
- [ ] `make test` passes

Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

**GitHub:**
```bash
gh pr create --base <default_branch> \
  --title "[<ticket-id>] type: short description" \
  --body "$(cat <<'EOF'
## Summary

**Ticket:** [<ticket-id>](<notion-url>)

- Bullet point describing what changed and why

## Test plan

- [x] `make lint` passes
- [ ] `make test` passes

Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- **title**: `[<ticket-id>] type: short description` (under 70 characters total)
- **base**: `master` or `main` -- use whichever `default_branch` was detected

Return the PR/MR URL to the user.

## Edge Cases

- **No git repo**: Stop and tell the user this only works inside a git repository.
- **Worktree path already exists**: If `.worktrees/<description>` already exists, append a suffix or ask the user for a different name.
- **Push rejected**: If push fails (e.g. remote has newer commits), run `git pull --rebase` first, then retry the push.
- **Multiple remotes**: Default to `origin`. If `origin` doesn't exist, list remotes and ask the user.
- **Notion CLI not found**: If `~/.claude/skills/notion/notion_cli.py` doesn't exist, skip the Notion step and warn the user.
- **User only wants ticket + MR update**: If the tree is clean and MR exists, skip commit/lint/push and go straight to Notion ticket + MR update.
