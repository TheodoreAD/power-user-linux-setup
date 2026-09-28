---
status: idea
updated: 2026-09-28
source_repo: github.com-personal/repo-tasks
source_session: 44be2918-1669-4d16-9f77-56535cc6ddeb.jsonl
source_moment: 2026-09-27T23:47:59Z
source_plan:
---

# "Run the gate first" does not survive parallel tool calls: a commit sent beside its gate lands red

## Context

`~/AGENTS.md`, "About to commit", says to run the repo's quality gate first, and "Composing a Bash
call" says independent calls issued in one response run in parallel. Nothing says a gate and the
commit it guards are **not** independent. So a session that batches them does satisfy the letter of
both rules: it ran the gate, and it batched the calls.

Kind of misuse, per session-harvest's three shapes: **followed and still produced the wrong
outcome**. The gate did run, but the commit did not wait for it, so the commit shipped whatever the
gate would have refused.

## Evidence

repo-tasks session `44be2918-1669-4d16-9f77-56535cc6ddeb`, around 2026-09-27T23:47Z. One response
held `inv quality.precommit` and
`git commit -m "Ask uv and gh for uncoloured output wherever this package parses it …"` as sibling
calls. The gate failed on `E501 Line too long (121 > 120)` in `src/repo_tasks/ci.py`, and the commit
(`3500732`) had already landed. It was caught because the gate's output arrived in the same batch,
and it was fixed by amending the unpushed HEAD (`6883908`). Pushed, it would have been a red CI run.
This is one occurrence in one session, and nobody has measured it yet.

**Added on absorption, 2026-09-28: the same enabling shape is already on record.**
`plans/2026-08-23-global-agents-md-adherence-watch.md` session 21 ends on a PITFALL naming it:
"batching dependent calls in one parallel response, where a later call cannot see an earlier one's
output". There, a derived SHA and an invented run ID were followed, in the same batch, by a pushed
commit claiming CI was green. So this is a second instance across two repos, with different rules
broken and one mechanism. That argues for stating the general rule once (a call whose precondition
is another call's result is never its sibling), rather than a clause in "About to commit" alone.
Separately, the adherence sample corpus holds a third candidate clause, a scan step in the commit
recipe, which touches the same section. Decide them together.

## Open questions

[NEEDS CLARIFICATION: a sentence in "About to commit" (the gate's call and the commit's call are
never siblings in one response, because the commit's precondition is the gate's exit code), or a
`session-bash-audit` pattern first, to learn the rate before spending always-loaded lines on it? The
audit sees Bash calls but not which ones shared a response, so it would need the transcript's
message grouping.]

## Recommended direction

Measure first with session-bash-audit: count a `git commit` whose response also contains a gate
call. If the rate is non-trivial, add one clause to "About to commit", ending on the shape to use:
the gate alone, then read its exit, then commit.
