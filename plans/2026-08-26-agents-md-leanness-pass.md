---
status: idea
updated: 2026-08-26
---

## Context

`~/AGENTS.md` measured **4,326 body words, 37 rules, 446 lines** across 8 clusters immediately after
the 2026-08-26 fragment split (`plans/2026-08-26-agent-artifact-authoring-decoupling.md`). Its own
review reference points, researched and recorded in `contributing/global-agents-md.md`, are **≤200
lines and ≤15 rules**. The last leanness pass (2026-08-23) landed it at ~2,500 body words / 30 rules
/ 294 lines, so it has grown by roughly 1,800 words and 7 rules since, with no review in between.

The split did not cause the growth — it moved rules between fragments and added none. It made the
growth visible, because `contributing/global-agents-md.md`'s measurement commands now read the
**assembled** result rather than a single source file, and that was the first time the current total
had been measured at all.

This plan exists because that finding currently lives as a sentence in
`contributing/global-agents-md.md` ("A leanness pass on `portable.md` specifically is the obvious
next one"), which is exactly the "don't stash future work in prose docs" failure the `plan-docs`
convention names: prose future-work has no status field, so nothing ever prompts a return visit.

## Why it matters, not just "the number is over"

The reference points are not arbitrary. From the research already in
`contributing/global-agents-md.md`: **bloated instruction files cause models to ignore instructions
wholesale**, not to selectively filter the irrelevant ones, and recall degrades as context grows.
Overlapping near-duplicate rules are a measured driver of that degradation. So the cost of being 2×
over is paid on every turn of every session in every repo, silently, and the rules most likely to be
dropped are not the ones anyone chose to sacrifice.

Where the weight sits, from the per-section measurement:

| cluster                        | words |
| ------------------------------ | ----- |
| Bash & tool use                | 919   |
| Git & commits                  | 691   |
| Research & design              | 669   |
| Verification                   | 528   |
| This machine & this setup      | 485   |
| Collaboration & output         | 433   |
| Claude Code specifics          | 432   |
| Agent instructions & knowledge | 169   |

`portable.md` holds the top four and is the obvious target; `this-setup.md` and `claude-code.md`
together are under 1,000 words and are not the problem.

## Open questions

[NEEDS CLARIFICATION: which lever first — **merge near-duplicates**, **demote to skills**, or
**shorten in place**? The research says merging overlapping rules is the change most likely to
improve adherence (real but modest, ~4–7pp), while demotion is the only one that actually removes
words from the always-loaded set. Shortening in place is the one the same research warns against
where a rule has been observed being missed: "strengthen its language rather than lengthen its
explanation" cuts both ways, and several of these rules are long precisely because a shorter version
was already tried and missed.]

[NEEDS CLARIFICATION: which rules are demotion candidates under the tier test — sharp statable
trigger, cheap and recoverable miss? `Bash & tool use` is the biggest cluster and the one with a
topic-owning skill (`session-bash-audit`) that can both hold guidance and _measure_ whether moving
it made adherence worse. That makes it the safest place to try demotion, and the riskiest to get
wrong, since its rules were rewritten specifically because they were being missed.]

[NEEDS CLARIFICATION: does the per-rule approval requirement make a pass this large impractical in
one session? `contributing/global-agents-md.md` states that moving a rule out of the always-loaded
set needs the same per-rule user approval as deleting it, and that nothing is deleted without
asking. At ~22 candidate rules in `portable.md` that is a lot of decisions. Batching them into a
handful of `AskUserQuestion` rounds by cluster is probably the shape, but it should be agreed before
starting.]

## Additions parked pending this pass

Two cross-repo preferences surfaced 2026-08-26 (harvest of the `agent-skills` scoping session) that
would otherwise be appended to `portable.md` right now. Parked here instead, per `session-harvest`'s
"destination mid-restructure → the plan reshaping it" filter: appending while the file's shape is
being decided bypasses the admission gate this pass exists to apply, and risks the addition being
restructured away unread. Both are recorded today only as `[DECISION:]` tags inside
`plans/2026-08-26-agent-artifact-authoring-decoupling.md`, which means that on that plan's
retirement they land in a PULSE `contributing/` page — and a page in this repo never fires in
`repo-tasks`, `scaffoldapy`, or a `*-polite-mcp` repo. That reach gap is the argument for admitting
them; the file's size is the argument against. Decide both at this pass's close, against
`contributing/global-agents-md.md`'s "Admitting a new rule" criteria, not before.

[DEFERRED: **"No vendor lock-in — the artifact vocabulary is `AGENTS.md`, Agent Skills and MCP;
anything vendor-specific is admissible only as harness plumbing that makes an agent work better,
never as a carrier for instructions or knowledge."** Tier-1 shaped on the face of it: it can fire on
any turn in any repo, and its miss is silent and expensive — a session designs against a vendor
mechanism and the work is thrown away, which is exactly what nearly happened before the constraint
was stated. No topic-owning skill covers it. Trigger for the heading, if admitted: "Choosing a
mechanism for agent instructions, skills, or tools".]

[DEFERRED: **"Prefer the mainstream community tool, and have PULSE verify its result rather than
reimplement it."** A _variant_ of the existing "About to author content, config, or a workaround
from scratch" rule rather than a new one — that rule already says reuse maintained upstream work;
the new half is what to do afterwards, namely check the result rather than rebuild the mechanism.
Per the admission criteria a variant extends its rule's existing section, so if admitted this is a
sentence appended there, not a heading. Concrete instance to cite: the `skills` CLI announces a
Claude Code symlink it does not create, and PULSE's own `_ensure_agents_skills` covers the gap
instead of PULSE reimplementing skill installation.]

## Recommended direction

Rough. Measure first with the two commands in `contributing/global-agents-md.md`'s "Re-measuring the
deployed file", so before/after is comparable with the 2026-08-23 numbers. Then take one cluster at
a time, largest first, and for each rule ask only the tier question — is the miss silent and
expensive, or sharp-triggered and recoverable? Merge before demoting, demote before shortening, and
re-measure after each cluster rather than at the end, so a pass that stops early still leaves the
file better than it found it.

Do not treat the ≤200/≤15 numbers as a target to hit in one go. They are review reference points,
and the discipline that actually keeps the file small lives upstream in the admission criteria — a
pass that trims 1,000 words while the intake gate stays open just schedules the next pass.
