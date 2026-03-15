---
name: push
description: |
  Go from uncommitted changes to a GitHub PR with a linked Notion ticket in one step.
  Checks git status, creates a branch/worktree if on main/master, commits changes,
  finds or creates a Notion ticket, pushes, and opens a PR following team conventions.
  Use whenever the user says "push", "ship", "ship it", "create PR", "open PR",
  "submit", "push changes", "/push", "wrap up", "send this out", or when the user
  has finished coding and wants to get their changes into a PR. Even casual phrases
  like "let's get this merged" or "I'm done, push it" should trigger this skill.
---

# Push

One-command workflow: uncommitted changes → commit → Notion ticket → GitHub PR.

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
- **remote_url**: to derive `owner` and `repo` (parse `git@github.com:owner/repo.git` or `https://github.com/owner/repo.git`)
- **default_branch**: `main` or `master` (from `HEAD branch`)

If the working tree is clean (no changes at all), tell the user "Nothing to push — working tree is clean" and stop.

## Step 2: Branch Strategy

### Already on a feature branch

If `current_branch` is NOT `main`/`master`, skip to Step 3. The branch is ready.

### On main/master with changes — create a worktree

The user is working directly on the default branch. Create a new branch in an isolated worktree at `~/Source/` so main/master stays clean and reusable for future worktrees.

1. **Ask the user** (via AskUserQuestion) for:
   - **Type**: `feat`, `fix`, `refactor`, `chore`, or `docs`
   - **Short description**: kebab-case, e.g. `sales-v2-filter-by`

   If the user invoked the skill with arguments (e.g. `/push fix: sales filter`), parse the type and description from those arguments instead of asking.

2. **Author prefix**: Use `$USER` environment variable.

3. **Construct the branch name**: `$USER/<type>/<description>` (e.g. `cle/fix/sales-v2-filter-by`)

4. **Create worktree with the changes**:
   ```bash
   git stash --include-untracked
   git worktree add ~/Source/<description> -b $USER/<type>/<description>
   cd ~/Source/<description>
   git stash pop
   ```

5. **Switch the session** to the new worktree directory. All remaining steps run from `~/Source/<description>`.

6. Tell the user: "Created worktree at `~/Source/<description>` on branch `<branch>`. After this session, start new sessions from that directory."

## Step 3: Commit

1. Run `git diff --stat` and `git diff` to understand the changes.
2. Stage relevant files explicitly (`git add <file> ...`). Avoid `git add -A` — never stage `.env`, credentials, or secrets.
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

If pre-commit hooks fail, fix the issues and create a NEW commit — never amend.

## Step 4: Lint

Run `make lint` to catch issues before pushing. If lint fails:

1. Read the error output and fix the issues (formatting, type errors, import order, etc.).
2. Stage the fixes and create a NEW commit (e.g. `fix: lint errors`).
3. Re-run `make lint` to confirm it passes.

Do not proceed to Step 5 until `make lint` passes.

## Step 5: Notion Ticket

Find or create a Notion ticket so the PR has a `[NEXT-XXXX]` reference.

### Search first

Use `mcp__claude-boy-stdio__search_tickets` to look for existing tickets in the current sprint. Filter by the likely assignee (the `$USER` name, e.g. `cle`).

Scan the results for a ticket whose title relates to the changes being committed. Consider:
- Keywords from the branch name or commit message
- The domain area being changed (e.g., "sales", "orders", "pipeline")

### Reuse or create

- **If a matching ticket exists**: Confirm with the user — "Found ticket `NEXT-XXXX`: '_title_'. Use this?"
- **If no match or user declines**: Create a new ticket:
  ```
  mcp__claude-boy-stdio__create_ticket
    title: Short description matching the PR
    description: Summary of the changes
    priority: "Medium"
    assignee: $USER
  ```

### Get the ticket ID

The Notion tool may not return the `NEXT-XXXX` ID directly. If the ID is not visible in the tool response, ask the user: "What's the ticket ID? (e.g. NEXT-2912)"

Store the ticket ID for Step 6.

## Step 6: Push and Create PR

### Check for existing PR

```bash
gh pr list --head <branch-name> --json number,url --jq '.[0]'
```

If a PR already exists, just push and tell the user "Pushed to existing PR: <url>". Done.

### Push

```bash
git push -u origin <branch-name>
```

### Create PR

Use `mcp__claude-boy-stdio__create_pull_request`:

- **owner** / **repo**: parsed from remote URL in Step 1
- **head**: current branch name
- **base**: `master` (or `main` — use whichever `default_branch` was detected)
- **title**: `[NEXT-XXXX] type: short description` (under 70 characters total)
- **body**:
  ```markdown
  ## Summary

  **Ticket:** [NEXT-XXXX](https://www.notion.so/<page-id>)

  - Bullet point describing what changed and why

  ## Test plan

  - [x] `make lint` passes
  - [ ] `make test` passes

  🤖 Generated with [Claude Code](https://claude.com/claude-code)
  ```

Return the PR URL to the user.

## Edge Cases

- **No git repo**: Stop and tell the user this only works inside a git repository.
- **Worktree path already exists**: If `~/Source/<description>` already exists, append a suffix or ask the user for a different name.
- **Push rejected**: If push fails (e.g. remote has newer commits), run `git pull --rebase` first, then retry the push.
- **Multiple remotes**: Default to `origin`. If `origin` doesn't exist, list remotes and ask the user.
