---
name: worktree-review-loop
description: |
  Isolated coder/reviewer loop using different models. Use for "code + review
  until it passes", "worktree review loop", "/loop-review", or "ship this
  with a reviewer".
---

# Worktree Review Loop

Parent-driven; no JS. Fresh children every pass, different coder/reviewer
models. **Cap: 5 passes** unless specified.

## Setup

- Verify host delegation, models, fresh contexts, and working-directory support.
  Stop on conflicting host rules.
- Resolve repo root, task slug, and branch following repo conventions
  (required type/ticket); inspect existing names or ask if unclear.
- Use `$REPO_ROOT/.worktrees/$SLUG`. Verify reused worktree/branch; otherwise
  require a clean source checkout and `git worktree add -b "$BRANCH" "$WT"`.
  Never stash/commit operator changes. Ensure `.worktrees/` is gitignored.
- Record task, absolute worktree, branch, original review base, models, pass/cap.
  Recover the original base on reuse.

## Loop

Launch sequentially in the worktree with fresh contexts. Prefer async; record
run ids and consume results via host notifications/wait tools. Fall back to
synchronous execution if unsupported. Parent may work elsewhere; one writer
in the worktree.

1. **Coder:** include task, worktree, branch, pass/cap. Implement first;
   subsequent fixers inspect prior code/commits and fix only full review
   findings. Run relevant tests/typecheck, commit, report changes/checks/SHA.
   Parent verifies result, checks, and worktree/commit state.
2. **Reviewer:** independent. Include task, worktree, branch,
   original base, and checks. Review cumulative diff and relevant code/tests;
   give evidence-backed file/line findings and final verdict:
   - `ok`: no blocker/major issues; stop.
   - `blocked`: fresh fixer with full findings, unless cap reached.
   - Missing/ambiguous verdict: stop; report incomplete review.

## Stop

Report verdict/findings, passes, worktree, branch. Failures: stop; report exact
error, run/status, repo/worktree/branch/ref, and partial diff—not fixer input.
Retry within protocol; switching, cap extension, merge/cherry-pick, and cleanup
require operator approval.
