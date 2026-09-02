---
status: idea
updated: 2026-09-02
source_repo: github.com-personal/agent-skills
source_session: 13aa58df-3551-49b7-ac0e-0c3693bf8221.jsonl
source_moment: 2026-09-02T17:05:00+03:00
---

# `research-update` moves every clone forward but cannot say whether moving one does anything

## Context

`research-library` gained `scripts/library.py` on 2026-09-02 (agent-skills, landed the same day).
Its `check` subcommand reads every entry in `$RESEARCH_HOME` against the store's own conventions:
provenance file present and complete, entry name still matching the clone's own `origin`, and
whether a `git fetch origin` in that clone can bring anything new at all.

That last one is the half `research-update` structurally cannot see. It refreshes every clone —
shallow fetch, hard reset — and reports success. A clone made with an explicit `--branch <tag>` has
a detached HEAD and tracks a ref that never moves, so the refresh succeeds, reports "up to date",
and the entry stays years stale. The trap is documented in `$RESEARCH_HOME/README.md`; nothing was
running the check.

**Confirmed 2026-09-02**, first run of `check` over the 52-entry library: one clone pinned that way
(`gitlab.gnome.org--GNOME--gnome-shell`), plus three `docs/` entries whose provenance is incomplete
or uses a `kind` outside the store's vocabulary. None of them is visible to a refresher, and none is
visible to any `git status` anywhere, because the store is not version-controlled.

## Recommended direction

Have `research-update` end by running the check and printing what it found:

```shell
python3 ~/.agents/skills/research-library/scripts/library.py check
```

Non-fatal by default — a refresh that worked should not exit non-zero because an unrelated entry has
a thin provenance file — with the count printed as the last line so it is what a reader sees.
`--strict` exists for the case where a caller does want a non-zero exit.

[NEEDS CLARIFICATION: does `research-update` want a hard dependency on an installed skill? It is
deployed to `~/.local/bin` from this repo and the skill is installed separately, so the check has to
degrade to a one-line "library.py not installed, skipping" rather than failing. The alternative —
vendoring the check into the script — duplicates a convention that belongs to the skill and would
drift from it, which is the failure this whole line of work is about.]

[NEEDS CLARIFICATION: should the refresher also fix what it finds — re-set a pinned refspec to the
remote's default branch? It is mechanical (`git ls-remote --symref origin HEAD`, then
`git config remote.origin.fetch`), but it rewrites a clone's configuration on the strength of a
guess about why it was pinned that way. Reporting is certainly right; repairing is a decision.]
