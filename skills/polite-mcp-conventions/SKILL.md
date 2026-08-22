---
name: polite-mcp-conventions
description: "Use when working in one of the *-polite-mcp personal automation repos (olx-polite-mcp, emag-polite-mcp, altex-polite-mcp, freshful-polite-mcp, temu-polite-mcp) or product-research-pipeline — implementing a new tool, running a live spike/CDP exploration against a real logged-in site, deciding whether an action needs confirmation before running it, or asking the user for several small per-item decisions (quantities, yes/no per item) during a reorder/shopping flow. Covers: confirming before the first live mutating action against a real personal account, batching interactive AskUserQuestion decisions instead of asking for a typed list, and writing spike/research findings into PLAN.md before or alongside implementing."
---

# Polite-MCP family: agent collaboration conventions

Behavioral conventions for this user's personal shopping/classifieds automation family — distinct
from `mcp-skill-shipping` (dev-loop/distribution mechanics for the same repos) and from
`~/AGENTS.md` (truly universal conventions). These are specific to the domain: automation against a
user's own live, logged-in personal accounts.

## Confirm before the first live mutating action

Before performing the _first_ real mutating browser action against the user's live, personal,
logged-in account in a session (e.g. a real add-to-cart click, not a dry read), stop and ask via
`AskUserQuestion` rather than just doing it — even when the action is narrowly scoped, low-cost, and
reversible. Frame it as a one-off scoped test (what will run, and that it'll be undone/reverted
afterward if applicable), not a generic permission request. Once approved and the shape/behavior is
confirmed, subsequent same-kind actions in the same session don't need re-confirming.

**Why:** this family already treats checkout/personal-account actions as a materially higher-stakes
category than plain reads — every repo's own boundary docs say so (e.g. "checkout is never
automated," no-CAPTCHA-solving). A first live mutation test against a real account fits that same
category even when the specific action itself is small. Confirmed live in `freshful-polite-mcp`
(2026-08-14): asking before the first add-to-cart test got a clean, low-friction "yes, test on one
cheap item" — the right default, not overcaution.

## Batch interactive per-item decisions, don't ask for a typed list

When a workflow needs several small independent decisions from the user (e.g. "how many of each of
these 8 items do you want?"), use `AskUserQuestion` in batches of roughly 4, with a recommended
default pre-filled as the first option — don't present a big list and ask the user to type out
answers for all of them in one reply.

**Why:** explicit feedback during a Freshful reorder-flow session — "suggest some quantities for all
those things, and ask me one by one, it needs to be interactive, if i have to type all that stuff
out it kills the ux." Typing a long structured reply is worse UX than a short guided Q&A, even
though both convey the same information.

**How to apply:** reserve a single free-text ask for decisions that aren't decomposable this way, or
where there are too many items for batching to stay lightweight — at that point, consider whether
the flow itself needs restructuring (e.g. splitting "items likely due" from "rarely-touched items"
rather than batching everything flat).

## Write spike/research findings into PLAN.md before or alongside implementing

When a research/spike phase (live CDP exploration, API probing, DOM inspection) turns up findings
that change or confirm the plan, write them into the repo's `PLAN.md` first — as their own section,
matching the doc's existing narrative style — before or alongside writing the actual implementation
code. Don't just carry findings in conversation and go straight to code.

**Why:** explicit instruction, `freshful-polite-mcp` (2026-08-14): "it's good to keep everything in
the plan, then implement." Matches the existing pattern across this repo family, where `PLAN.md` (a
single monolithic file — this family predates the `plans/YYYY-MM-DD-topic.md` convention documented
in the `plan-docs` skill, and hasn't been migrated onto it) is the durable record of _why_ the
architecture looks the way it does; code comments point back to it rather than re-explaining.

**How to apply:** after any live-spike/research pass in one of these repos, update `PLAN.md`'s
relevant section(s) — mark resolved open questions, add a dated findings section, restate/extend any
boundary decisions the findings touch — before moving on to implementation. Do this even when the
user hasn't explicitly asked for the write-up that round; treat it as the default sequencing.
