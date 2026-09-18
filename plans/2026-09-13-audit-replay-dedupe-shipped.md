---
status: idea
updated: 2026-09-13
source_repo: github.com-personal/agent-skills
source_session: 7edc112d-9033-4253-b9ff-0c75fd61c23e.jsonl
source_moment: 2026-09-13T17:11:23+03:00
source_plan:
---

# The audit's replay dedupe has shipped, so finding 2's baseline needs no inflation note

## Context

`plans/2026-09-12-imperative-vs-rationale-in-instruction-files.md` holds finding 2 until the
`cut-message` denominator arrives, and its closing `[UNVERIFIED:]` says: take a fresh baseline when
it lands, and _"note in that baseline's `--note` that the audit's absolute-count rows were still
inflated by resumed transcripts unless `agent-skills` has shipped the dedupe by then."_

It has. This reports a fact for that condition; the decision stays with that plan.

## Evidence

- **Shipped** as `agent-skills` `28099cd`, pushed 2026-09-13 and installed on this machine the same
  day. It came from the filing `2026-09-13-audit-counts-a-resumed-sessions-calls-twice.md`, absorbed
  into and landed in `agent-skills`.
- **What changed:** `load_calls` keeps one copy of each call a resumed transcript replayed, keyed on
  the `tool_use` id. Measured before choosing it: all 649 replayed calls in that seven-day window
  kept their id. The corpus header now prints
  `N more were copies a resumed transcript replayed from its parent, counted once`.
- **Baselines** now record `replayed_dropped`. `--compare` against one without it, which includes
  `~/.local/state/session-bash-audit/2026-09-12.json`, prints that the baseline predates the dedupe
  and that part of any delta against it is the fix.
- **Size of the effect,** seven days to 2026-09-13: rates moved at most 0.43pp (`head/tail`), and
  small counts moved most. `cut-message` went 7 → 5 and `git-add-all` 19 → 12.

The other filing from that plan's session,
`2026-09-13-compare-does-not-say-when-the-windows-differ.md`, also landed the same day, as
`agent-skills` `26f823b`. `--compare` now prints both windows when they differ, and **`cut-message`
prints its own population**: hits over calls carrying a commit or `gh` message, in the session view
and the comparison cell. Re-run on the case that plan was filed from,
`--days 3 --compare 2026-09-12.json` reads `cut-message=3/329`. So the denominator that plan
computed by hand is now printed, but it covers the whole window rather than splitting at `2f21557`.
The before/after split still has to be taken with `--until`, or from the `--json` dump.

## Open questions

None for this filing.

## Recommended direction

When finding 2 lands, take the fresh baseline with the installed audit and drop the inflation clause
from its `--note`. The dedupe applies to that baseline on its own, and `replayed_dropped` records
it. Read `cut-message` as the printed `hits/population`, taken after `2f21557` (`--json` gives the
timestamps to split on), rather than as a count against a baseline.
