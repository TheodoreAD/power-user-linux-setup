---
status: idea
updated: 2026-08-22
---

## Context

Surfaced 2026-08-22 while working in `repo-tasks`: `skills/python-conventions`'s `description`
frontmatter under-triggers on exactly the requests it's meant to cover. Its testing-conventions
clause reads `test structure (DAMP vs DRY, fixture scope)` — internal vocabulary the skill uses
about itself — rather than the words a real request contains (`pytest`, `fixtures`, `parametrize`,
`write
tests`). Claude Code decides whether to invoke a skill by matching the request against that
description text before ever loading the file, so a description built from a topic's own jargon
instead of the request-side vocabulary a user/agent would actually type is a structural miss, not a
one-off fluke — it happened mid-session even with the skill's own author present in the
conversation.

This is a `skills/` family-wide risk, not a one-file problem: every skill here (`db-defaults`,
`mcp-skill-shipping`, `plan-docs`, `python-conventions`, `research-library`, `session-harvest`) has
exactly this same single point of failure — one dense `description` string, hand-written once, never
mechanically checked against the vocabulary real requests would use. No current process re-reads a
skill's description from the "cold request" side after it's written.

**Before building anything custom: Claude Code already ships at least two things aimed at this exact
problem space, unconfirmed whether either actually covers this repo's skills.** `claude plugin
eval`
(writing/running plugin eval suites, JSON/report output, sandbox, CI, early-access enablement) and a
`/skill-doctor` report — both referenced by the `claude-code-guide` subagent's own description in a
live session, meaning they're real, documented, current features, not something half-remembered.
Neither has been read in detail yet. Open question below: do either apply to a personal,
non-marketplace `.agents/skills/`-sourced skill installed via this repo's own `inv
ai.skills`
(`tasks/ai.py`), or are they scoped specifically to skills packaged and distributed as a Claude Code
"plugin" (a different distribution mechanism from this repo's
`{ source = "local", path
= "skills/<name>" }` / `{ source = "skills-cli", ... }` model in
`setup.toml`)? If they apply as-is, this plan is mostly "go read the docs and run the tool," not
"build something."

## Open questions

[NEEDS CLARIFICATION: what exactly does `claude plugin eval` check, and does it (or could it easily)
validate a skill's `description` against a corpus of realistic trigger phrases — i.e. does it catch
the python-conventions under-triggering case, or does it check something orthogonal (tool
permissions, sandboxing, whether the skill file is well-formed) that wouldn't have caught this?]

[NEEDS CLARIFICATION: what does `/skill-doctor` actually report, and does it run against
locally-authored `.agents/skills/` content the way this repo's skills are structured, or only
against plugin-packaged skills pulled from a marketplace?]

[NEEDS CLARIFICATION: beyond Anthropic's own tooling, is there existing community writing/tooling on
what makes an Agent Skill (or, more broadly, a tool/function description for an LLM) reliably
trigger — e.g. prompt-engineering guidance on writing tool descriptions with the caller's vocabulary
rather than the domain's internal vocabulary? This is a well-trodden problem in function-calling/
tool-use contexts generally, not unique to Claude Code Skills — worth a real, hands-on-depth search
pass (matching this user's usual bar for tool/library research, not a single search) before assuming
nothing's been written.]

[NEEDS CLARIFICATION: if neither Anthropic tool nor existing community material fully covers this,
what's the minimal version worth building? Candidate shape: a small reviewer skill/script that, for
each `skills/<name>/SKILL.md`, generates or is fed a handful of realistic natural-language requests
a user/agent might type for that skill's actual content, and checks (via a fresh, context-free model
call — the same "cold" condition a real trigger decision happens under) whether the _description
alone_ would surface the skill for each one. Low-boilerplate, matching this repo's own bias — not a
generalized eval framework if a handful of realistic-request checks already catches drift like the
python-conventions case.]

## Recommended direction

Research first (`claude plugin eval`, `/skill-doctor`, and general tool-description/function-calling
trigger-reliability literature) before writing any new tooling — a real hands-on-depth comparison,
not a decision made on one search pass. If existing tooling already covers this repo's skills, wire
it in (likely as a step `inv ai.skills` or a dedicated task runs) instead of building a parallel
mechanism. If it doesn't, build the smallest version that would have actually caught the
python-conventions gap — a real, concrete test case to validate against before considering the tool
done.
