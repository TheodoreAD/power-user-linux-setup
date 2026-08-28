---
status: in-progress
updated: 2026-08-29
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

This machine runs parallel sessions on the same repos, and at least one other session has been
committing here today. A rewrite changes every SHA from the earliest rewritten commit onward, so any
session holding an unpushed commit above that point has to reset onto the new history afterwards.
Check for other live sessions before starting, not after.

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

### 4. What remains: the support request

The force-push is done; the purge is not. Measured minutes afterwards,
`gh api repos/TheodoreAD/power-user-linux-setup/commits/3c0b606…` still returned the commit and four
matches for the addresses in its patch. Unreachable is not deleted, and GitHub serves by SHA.

The request text, the commits to name (the four on the old `master` plus thirteen old `gh-pages`
build commits), what a support request cannot reach, and the 404 that verifies it are all in
`agent-skills`' `plans/2026-08-29-github-support-cache-purge.md`, which covers both repos rather
than splitting one errand across two files.

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

[UNVERIFIED: the support request, which is the only thing that stops the old commits being served.
Tracked in `agent-skills`' `plans/2026-08-29-github-support-cache-purge.md`; the test is that
`gh api .../commits/3c0b606…` returns 404.]
