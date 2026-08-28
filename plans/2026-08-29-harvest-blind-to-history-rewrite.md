---
status: idea
updated: 2026-08-29
depends_on: [agent-skills]
---

## Context

Queued here rather than edited into `agent-skills` directly: that repo is mid-surgery (one unpushed
commit, `plan-docs`' store work in flight), and `session-harvest`'s own guidance now says a
candidate owed to a repo under restructure goes to a `depends_on`-tagged plan in the repo that found
it.

**`session-harvest`'s live-state sweep cannot tell that the session's own commits were rewritten out
from under it.** Step 5's git bullet checks three things — dirty tree, unpushed commits, whether the
remote moved — and all three assume the commits still exist. After a parallel session's
`filter-branch` and force-push, every one of them reads healthy:

- `git status` — clean
- `git rev-list --left-right --count origin/master...HEAD` — `0 0`, perfectly in sync
- `git log origin/master..HEAD` — empty, nothing unpushed

And yet every SHA this session recorded is gone. Measured 2026-08-29: five commit IDs from the
previous harvest report in this same session (`git cat-file -e <sha>^{commit}`) all returned
non-zero. The content survived under new IDs; the identifiers did not.

The cost is specific and not hypothetical. The prior harvest report in this session listed "5
unpushed commits" **by SHA** and told the user which one un-reds CI. Had the rewrite happened a few
minutes earlier, that report would have named five phantoms and sent the user looking for commits
that do not resolve — with every check the skill prescribes still coming back green.

## Open questions

[NEEDS CLARIFICATION: is the right check "do my recorded SHAs still resolve", or the broader "did
the branch I am on get rewritten"? The first is cheap and directly catches the reporting failure,
but needs the session to have recorded SHAs to check. The second (compare `git reflog` or the
merge-base against what the session saw at its start) catches it even when nothing was recorded, at
the cost of state the harvest does not currently keep. Lean the first, because the failure that
matters is a report naming dead IDs — and if nothing was recorded there is nothing to misreport.]

## Recommended direction

Two additive edits to `skills/session-harvest/SKILL.md`, both small.

**1. Step 5, the git bullet.** Add a sentence after "whether the remote moved under you":

> …and whether the commits you recorded still resolve (`git cat-file -e <sha>^{commit}`). A parallel
> session's history rewrite leaves a clean tree, an in-sync branch and an empty unpushed list, while
> every SHA you noted is gone — so report commits by **subject**, which survives a rewrite, not by
> ID, which does not.

**2. Step 8, the report section.** One clause under "Persisted this pass": name commits by subject
rather than SHA, for the same reason. A harvest report is read after the session, which is exactly
when a rewrite may already have happened.

Both changes are worth having in `plan-docs` too, one level up: **16 commit citations across 5
tracked files in this repo stopped resolving** after the purge — recorded with the count and the
detection one-liner in `plans/2026-08-28-published-history-purge.md`. `plan-docs`' retirement
procedure already insists on grepping inbound _path_ references before deleting a file; a purge
breaks inbound _commit_ references instead, en masse, and no gate catches either the first time.

Applied in this repo already, as the pattern to copy: the SSH plan's "What has landed" table and
this repo's github-issues plan now name commits by subject and say why.
