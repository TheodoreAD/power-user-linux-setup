---
status: idea
updated: 2026-08-29
repo: git@github.com:TheodoreAD/power-user-linux-setup.git
---

## Context

Harvested 2026-08-29 from a long `agent-skills` session that reworked `plan-docs`. Two cross-repo
preferences surfaced that belong in the assembled `~/AGENTS.md`, so they belong in this repo's
`config/agents-md/` fragments. Filed here rather than committed into this repo's tree, per the rule
that same session built: a session that does not own a repo does not write into it.

`~/AGENTS.md` stands at **39 rules / 547 lines**, well past its own stated reference points of ≤15
rules and ≤200 lines. Both items below are written as **extensions to sections that already exist**,
so neither adds a heading and the rule count does not move.

## 1. The plan-mode rule contradicts the user (correction, not an addition)

`config/agents-md/portable.md:347`, "A narrow check grows into design work", currently says:

> When a "just check/confirm X" request starts revealing design decisions with real trade-offs,
> proactively suggest or move into plan mode rather than continuing to edit inline

The user, 2026-08-29, verbatim: _"you can write a plan in md, i don't like plan mode because it
creates files in other places than the ones we typically use."_

[DECISION: the rule's **intent** is right and its **mechanism** is wrong. Scope growing unnoticed is
a real failure and the rule should keep warning about it; what it should not do is name plan mode as
the response. The correct response on this machine is a `plans/*.md` file via the `plan-docs`
convention, which puts the design in the repo it belongs to, under version control, where the rest
of the planning already lives. Plan mode writes somewhere else entirely, which is the user's stated
objection.]

Suggested edit — replace the "suggest or move into plan mode" clause, keep everything around it:

> …proactively write the design into a `plans/*.md` file (the `plan-docs` convention) rather than
> continuing to edit inline. Do not reach for plan mode: it stores the plan outside the directories
> this machine's work actually uses. "Implement and document …" is still clear approval to execute
> for real…

The trailing sentence about exiting plan mode needs rewording to match, since there is no mode to
exit — the approval signal it describes is still correct.

## 2. Data flowing outward to a vendor is a cost, not a neutral default

The user, 2026-08-29: _"as a general rule, we dislike data flowing out to vendors."_ Stated while
reviewing a feature whose report publishes to a vendor by default.

It is general, it is not tied to one repo, and its miss is silent: a default-on upload succeeds
quietly, and nobody discovers it by observing normal behaviour. That is the shape the always-loaded
file is for.

[DECISION: extend the existing publishing/confidentiality cluster rather than opening a heading —
this is a variant of a principle already framed there (what leaves this machine, and what cannot be
taken back), applied to vendor features instead of to repo content.]

Suggested text:

> **A feature that uploads, publishes or phones home by default is a decision, not a default.** Pin
> the flag off deliberately and record why, rather than accepting the behaviour because it shipped
> that way. This applies to report publishing, telemetry, and any "share with the vendor" toggle;
> the reasoning is the same one that keeps the plans store without a remote — local costs nothing
> and cannot be taken back later.

## Evidence, if it helps the edit

Both came out of the same session. The vendor rule was prompted by `claude plugin eval`'s HTML
report, which publishes to claude.ai by default (`--no-publish` opts out) — recorded with the rest
of that research in `agent-skills`' `plans/2026-08-22-skill-trigger-quality-review.md`.

[DEFERRED: the same session found 75 commits across four public repos carrying `Claude-Session:`
URLs, and the fix for that is `attribution.sessionUrl = false` in this repo's generated
`settings.json`. That is filed separately as `2026-08-29-attribution-session-url-off.md` in this
same directory — the two are related but the settings change is mechanical while these are wording
changes, so they are kept apart.]
