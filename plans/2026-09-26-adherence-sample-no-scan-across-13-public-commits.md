---
status: idea
updated: 2026-09-26
source_repo: github.com-personal/repo-tasks
source_session: 86d02b45-c393-4ecd-96a7-75d16974465d.jsonl
source_moment: 2026-09-26T14:07:42Z
source_plan: plans/2026-09-02-agents-md-adherence-sample-corpus.md
---

# Adherence sample: 13 commits to a public repo, no staged scan

## Context

**Evidence for `plans/2026-09-02-agents-md-adherence-sample-corpus.md`, not a new topic. Merge it
there.** That plan already records the shape at its line ~1134: "8 commits and 2 pushes to a public
repo and ran `plans.py scan` zero times". This is one more session with the same shape, from a
`repo-tasks` session on 2026-09-26, found by its own harvest.

## Evidence

Session `86d02b45-c393-4ecd-96a7-75d16974465d.jsonl`, under the repo-tasks project directory in
`~/.claude/projects/`, 10:55Z to 14:07Z.

- **13 commits to `repo-tasks`**, which is public, from `7e3d4b0` to `8dca00b`, including a release
  bump. **7 pushes** to its `main`, plus a tag push for `v0.4.0`. The session made **no
  `scan --mode staged` call before any of them**, and no scan at all until the harvest.
- **One plans-store push made with bare `git -C ~/plans push`**, not with `plans.py push`, which
  scans the outgoing range first. It published 8 commits, 6 of them other sessions'. `plan-docs` was
  not yet loaded in that session; it was invoked in the same tool batch as the push.
- **The harvest's retroactive scans came back clean.** `scan --mode history` over `repo-tasks` and
  over the shareable store both reported 0 hits against 61 terms. As the corpus plan already notes,
  a clean history scan afterwards looks identical whether or not the gate ran.
- **The rest of the session's Bash adherence was clean:** 133 calls, with 0% chain, head/tail,
  exit-masked, cd-own-repo and git-C-own-repo. The one `git-C-mutating` row is that store push. So
  this is not a session ignoring the file in general. The skipped rule is the one whose command is
  not part of the commit shape the session had drilled in.

## Recommended direction

Count it as a sample in the corpus plan. The detail that may matter for the fix: the global rule
sits under "Committing to a repo that is or might become public", and this session's commits all
came through the "Writing the commit command" section's one-shape recipe. That recipe contains no
scan, so a session following it exactly still skips the gate.
