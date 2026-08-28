---
status: in-progress
updated: 2026-08-29
scheduled: 2026-09-01 or later — paused deliberately, see "Still open"
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

### 1. Prerequisite: SSH — resolved, and not what it looked like

[PITFALL: "ssh is broken until the restart" was half true and cost a day of sequencing. `git fetch`
did fail, but `inv ssh.check` showed why: this shell's agent was the empty one while
`/run/user/1000/keyring/ssh` held every key. One `SSH_AUTH_SOCK=/run/user/1000/keyring/ssh` prefix
per git command was enough to fetch and push today, with no restart. The rule the same task now
states — run `inv ssh.check` before concluding anything about ssh — is exactly the rule that was
skipped.]

Fetch first, then rewrite, then push, so `--force-with-lease` has a real value to lease against.

[PITFALL: a lease is only as good as the SHA handed to it. A push leased against a 40-character SHA
that had been _completed from the short form by hand_ rather than read from `git rev-parse` was
rejected as stale info. That rejection is the mechanism working; the fix is to read the value, never
to reconstruct it.]

### 2. Coordinate before rewriting

This machine runs parallel sessions on the same repos, and at least one other session was committing
here during the first pass. A rewrite changes every SHA from the earliest rewritten commit onward,
so that session's commits come out with new IDs and unchanged content.

[PITFALL: **the parallel sessions share one clone, so the usual advice is wrong here.** The reflex —
"the other session must `git fetch && git reset --hard` or its next push resurrects the old history"
— assumes a second clone holding the old objects. Checked 2026-08-29, after telling the user exactly
that: `git worktree list` shows a single checkout per repo and there is no second clone on the
machine. Both sessions drive the same `.git`, so the rewrite applied to the only history that exists
and there is nothing to reset. What is actually stale is the other session's _context_: SHAs it
recorded for its own commits no longer resolve, because the objects were gc'd. A confusion risk when
it refers back to its own work, not a data risk.]

What coordination is still for: `filter-branch` refuses to run against a dirty tree, so a session
mid-edit aborts the rewrite rather than losing work — which is the safe failure, but it wastes the
run. Check that the tree is clean and no session is mid-commit before starting.

### 3. The rewrite — done 2026-08-29

`git filter-branch -f --tree-filter` with a redaction script that aborts if any known-private form
survives. One pass over `master` (448 commits; the 31 below `5445a6a`, dated 2026-08-08, keep their
original SHAs, the 417 above it were renumbered), force-pushed to `e86fe4d`. Tip tree `52d8522`,
unchanged. Author and committer timestamps are preserved by `filter-branch` — verified against the
copy GitHub still serves of a pre-rewrite commit, same instant in both fields.

`git-filter-repo` was still not installed and the fallback was enough; the `[packages.*]` entry is
worth adding anyway, before the next time.

[PITFALL: `origin/land-on-master` was folded into the rewrite on the strength of a
`git branch -r --contains` hit, and the branch **did not exist on GitHub at all** — a non-pruning
`git fetch` had kept a deleted branch's remote-tracking ref alive for weeks. `gh api .../branches`
is the answer to "what branches does the remote have"; a remote-tracking ref is a local cache and
answers a different question. `git fetch --prune` cleared it.]

The three `initial-version*` branches were checked over their full histories, not just their tips:
zero occurrences. They needed nothing.

### 3a. `gh-pages` — deleted and rebuilt, not filtered

The built site is generated output, so the cheap purge is to drop the branch and let the workflow
republish from the now-clean `docs/`. Done: 26 hits across the old build commits, 0 in the rebuilt
branch, which is a single commit.

[PITFALL: deleting the branch unset **GitHub Pages** — the site 404'd until the Pages source was
pointed back at `gh-pages` via the API. `gh api repos/<owner>/<repo>/pages` returning 404 means "no
site configured", not "still building". Re-enable in the same session that deletes, or the docs are
down for as long as nobody looks.]

[DECISION: the workflow keeps appending to `gh-pages` rather than getting `force_orphan: true`.
Settled with the user 2026-08-29: being able to return to a previous render may be worth something,
and the reasoning is not finished. The one-time deletion above got rid of the exposed builds without
committing to an answer.]

[DEFERRED: whether built-site history is worth keeping at all. If it is not, `force_orphan: true` in
`publish_on_push.yml` makes every deploy replace the branch, and this class of exposure cannot
accumulate in generated output again.]

### 4. Still open: a 2021 string the first pass missed

A pyenv virtualenv named after an employer — `<employer>-gae-test-app`, in `scripts/python.sh`, in
the repo's **first two commits** (`a0bf1b9`, `15a7621`, March 2021). Long gone from the tip, still
in published history, and reachable from four branches. The exact string is deliberately not written
here (this repo is public and the scanner would flag this file); get it from
`plans.py scan --mode history --path <this repo>`, which prints it with its line, or from
`git show a0bf1b9:scripts/python.sh`:

| ref                           | carries it                         |
| ----------------------------- | ---------------------------------- |
| `master`                      | yes — whole history would renumber |
| `initial_version`             | yes                                |
| `initial-version-ubuntu-2004` | yes                                |
| `initial-version-ubuntu-2404` | yes                                |
| `gh-pages`                    | no — rebuilt clean                 |

[PITFALL: **the first pass missed it because the inventory was hand-written.** The survey pattern
covered the four addresses and the one sentence already known about — narrower than the scanner's
derived list, which carries every work root and found this in a single run. A tool was built
precisely because reading carefully misses things, and then the survey was done by reading
carefully. Never hand-roll the pattern: `plans.py scan --list-terms` is the list, and
`scan --mode history` is the audit.]

Ready to go, not yet run: the redaction script in that session's scratchpad already carries the
extra replacement and was dry-run against the real 2021 blob (it rewrites the virtualenv name to
`employer-gae-test-app` and exits 0). If the scratchpad is gone by then, rebuilding it is one
`(old, new)` pair plus the same term in its survivor check — take `old` from the scanner output
above rather than from this file.

[NEEDS CLARIFICATION: rewrite the three `initial-version*` snapshot branches, or delete them from
the remote? They are frozen markers, untouched for a year; deleting removes the exposure outright
and leaves one branch to rewrite instead of four. Rewriting keeps the markers and costs three local
branches plus three force-pushes. Decide before the next pass, not during it.]

Because the reach starts at the repo's first commit, this pass renumbers **every** commit on each
branch it touches — including the 31 that the first pass left alone.

### 5. What remains after that: the support request

The force-push is done; the purge is not. Measured minutes afterwards,
`gh api repos/TheodoreAD/power-user-linux-setup/commits/3c0b606…` still returned the commit and four
matches for the addresses in its patch. Unreachable is not deleted, and GitHub serves by SHA.

**Send this repo's request only after the pass above lands.** A second rewrite creates a second set
of unreachable commits, so a request sent now would be answered and then immediately be out of date.
`agent-skills` has no such dependency — its purge is complete and its request can go whenever.

The request text, the commits to name, what a support request cannot reach, and the 404 that
verifies it are in `agent-skills`' `plans/2026-08-29-github-support-cache-purge.md`, which covers
both repos rather than splitting one errand across two files.

### 5. Expected residue, so a future audit is not misread

`plans.py scan --mode history` will **never** reach 0 in this repo, and that is deliberate. Old
commits name the vendor of a meeting app and of a widely-deployed VPN client — in a support-forum
link and in that client's install paths under `/opt/`. One term covers both that vendor and a client
this user has worked for, and the scanner cannot tell the two apart. Rewriting the install paths
would make historical docs factually wrong, which is worse than a benign product mention, so the
residue is a recorded judgement rather than a miss. The working tree scans 0, and that is what the
pre-commit check actually uses.

[PITFALL: the first draft of the paragraph above named the vendor while explaining why the vendor's
name is tolerable, and `scan` refused the commit — a tree that had just been cleaned to 0 went back
to 2 hits. Writing _about_ a private term reintroduces it; describe the shape here too.]

## Files touched

- `plans/2026-08-28-ssh-add-and-askpass-friction.md` — already redacted at `05e8a8f`; history still
  carries the addresses.
- `docs/` sentence — already gone from the tip; history only.
- `setup.toml` — `[packages.git-filter-repo]` still unwritten; the fallback carried this round.

## Verification

Done 2026-08-29:

- `master`: 0 private hits across its full history; tip tree `52d8522`, byte-identical to
  pre-rewrite; `inv quality.precommit` green (388 tests); `origin/master` = `e86fe4d`.
- `gh-pages`: 1 commit, 0 hits; the published site returns 200 after Pages was re-pointed at it.
- The file GitHub now serves for the ssh plan has zero addresses in it.

[UNVERIFIED: the second rewrite (the 2021 string) and the support request. Neither has run.]

## Why this is paused rather than urgent

Settled with the user 2026-08-29, and worth writing down because it is the judgement that sets the
priority rather than a technical fact: the repo's 6 stars are from ex-colleagues who used an early
version of this guide, at the very companies the leaked names belong to. Nobody is expected to clone
it, and the people most likely to have seen it already knew. That does not make the remaining string
acceptable — it makes it a scheduled task rather than an emergency.
