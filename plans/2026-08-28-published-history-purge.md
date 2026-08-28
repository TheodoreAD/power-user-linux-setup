---
status: blocked on ssh access, which needs the restart this machine has not had yet
updated: 2026-08-28
depends_on: [agent-skills]
---

## Context

This repo is public. Two things in its published history identify employers and clients, and a
working-tree redaction does not remove either of them — only a history rewrite and a force-push
does.

Found 2026-08-28 by an audit run from `agent-skills`, and reproducible with the scanner that audit
produced (`skills/plan-docs/scripts/plans.py scan --mode history --path <this repo>`):

1. **Four work email addresses**, in a committed listing of SSH key filenames —
   `plans/2026-08-28-ssh-add-and-askpass-friction.md`, added in `3c0b606` and reshaped in `660b202`,
   both on `master`. The most identifying content in either repo. The working tree is redacted as of
   `05e8a8f`; history is not.
2. **A retired doc's sentence naming three employers** as hosts an `~/.ssh/config` had been carried
   across. In `master` history at `5445a6a` and `32e73f0`, and in roughly fourteen `deploy:` commits
   on `gh-pages`, which is where the built docs site is published from. The **tip** of `gh-pages` is
   clean — the live site does not show it — so this is history-only, on both branches.

`c16bc2b` separately removed a product vendor's name from `setup.toml` and `docs/webex.md`; that one
disclosed nothing, but it was the last thing keeping the scanner from reporting this repo clean, and
a gate that can never reach zero stops being run.

[DECISION: **Purge, don't leave it.** Settled with the user 2026-08-28, for this repo and for
`agent-skills` together. The alternative — redact forward and let the history stand — was rejected
because the content is other people's identities rather than the author's own, and a public repo's
history is as readable as its tip.]

## Design

### 1. Prerequisite: SSH, which needs the restart

`git fetch` and any push fail on this machine right now; the agent is empty and the fix landed in
`plans/2026-08-28-ssh-add-and-askpass-friction.md` but needs a restart to take effect. Until then
`origin/master` is a stale local ref, which also means `--force-with-lease` has nothing trustworthy
to lease against. **Fetch first, then rewrite, then push** — in that order, so the lease is real.

### 2. Coordinate before rewriting

This machine runs parallel sessions on the same repos, and at least one other session has been
committing here today. A rewrite changes every SHA from the earliest rewritten commit onward, so any
session holding an unpushed commit above that point has to reset onto the new history afterwards.
Check for other live sessions before starting, not after.

### 3. The rewrite

One pass per branch, over the full history rather than a range — the range form leaves the private
text visible in the `-` lines of the commit that removed it, which is exactly what happened in
`agent-skills`' first pass:

- `master` — the key listing in the plan file, and the retired doc's sentence.
- `gh-pages` — the same sentence, in the built site, across the `deploy:` commits.

`git-filter-repo` is the right tool and is **not installed**; installing it belongs in `setup.toml`
as a `[packages.git-filter-repo]` entry rather than a one-off, per this repo's own rule. The
fallback already used once in `agent-skills` is `git filter-branch --tree-filter` with a redaction
script that exits non-zero if anything private survives, so a partial rewrite aborts instead of
producing a half-clean history.

[PITFALL: `--prune-empty` did not drop the redaction commit in `agent-skills`, because a formatter
reflow left it with a two-line diff. Expect a surviving commit whose message describes a redaction
its diff no longer contains, and reword it in the same pass with `--msg-filter`.]

### 4. Force-push both branches, then ask GitHub to purge

A force-push replaces the branch; it does not make the old commits unreachable to anyone who knows a
SHA, and GitHub serves them until its own garbage collection runs. Ask GitHub Support to purge
cached views for both branches once the push lands. This repo has 6 stars and 0 forks — the stars
mean existing clones are plausible, and nothing can be done about a clone already taken.

## Files touched

- `plans/2026-08-28-ssh-add-and-askpass-friction.md` — already redacted at `05e8a8f`; history still
  carries the addresses.
- `docs/` sentence — already gone from the tip; history only.
- `setup.toml` — add `[packages.git-filter-repo]` before the rewrite, so the tool arrives the way
  every other tool on this machine does.

## Verification

- `plans.py scan --mode history --path <this repo>` returns **0 hits** after the rewrite. It is 0 on
  the working tree already, as of `c16bc2b`.
- `git log --all -p` on a fresh clone of the pushed result, greped for the four addresses and the
  employer names, returns nothing.
- The rendered docs site still builds and the `gh-pages` tip renders identically — the sentence
  being purged is not in the current build.

[UNVERIFIED: every step above. Nothing here has been executed — SSH is down, and the tooling is not
installed yet.]
