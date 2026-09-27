---
status: idea
updated: 2026-09-26
source_repo: github.com-personal/agent-skills
source_session: 8db05b10-386d-41aa-884b-890e81fdada7.jsonl
source_moment: 2026-09-26T19:12:00Z
source_plan:
---

# Two adherence instruments changed on 2026-09-26, so older corpus rows are not comparable on them

## Context

This repo's adherence plans record rows produced by agent-skills' `audit.py` and
`harvest.py claims`: `plans/2026-08-23-global-agents-md-adherence-watch.md` and
`plans/2026-09-02-agents-md-adherence-sample-corpus.md`. On 2026-09-26 agent-skills changed what two
of those rows count. A comparison across that date measures the instrument as well as the session.

## Evidence

- **`9579e9c`, `audit.py`:** `git-mutating` and `git-C-mutating` now match with quoted strings
  blanked. **The change can only lower these counts.** Text inside a `python3 -c "…"` string or an
  `rg "…"` pattern no longer counts, and `git-mutating-in-chain` follows `git-mutating`. On the
  session that reported it (`10d0c6cd-…`, harvested in this repo), `git-C-mutating` went from 4 to
  1.
- **`558c814`, `harvest.py claims`:** the gate-green matcher now also counts a success word paired
  with a test count ("Green, 707 tests", "N tests pass", "all N pass", a pytest-style "N passed").
  **The change can only raise this count.** Across this machine's transcripts it added 53 matching
  lines to 1,135.
- Both commits are on agent-skills `main`, and the installed copies were refreshed the same day.

## Recommended direction

When a corpus row is next compared against one recorded before 2026-09-26, say that it straddles
this change for `git-C-mutating`, `git-mutating-in-chain` and the claims count, and in which
direction each moved. Per session-harvest's instrument rule, a straddle voids only the rows the
change touched, so every other row stays comparable. Nothing needs re-running unless a comparison
actually turns on one of these rows.
