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

## Research findings (2026-08-22, second pass)

**`claude plugin eval`**: confirmed real (embedded early-access reference, corroborated by
independent third-party write-ups — Scott Spence, Medium, pasqualepillitteri.it) but **absent from
public docs** (`plugins-reference.md`, the docs map) and **gated early-access, not enabled for this
account**. What it actually checks: full scenario runs in sandboxed sessions, graded by `regex`,
`tool_used`, `tool_order`, `file_exists`, an `llm` judge (2-of-3 vote), and a `baseline`
with/without comparison — i.e. it's built to test a plugin's *behavior once invoked*, not
specifically description-only cold-trigger matching. `skill-creator` (a separate, related
early-access feature) is the one that's actually purpose-built for this repo's exact problem: it
analyzes a skill's `description` against sample prompts, flags false positives/negatives, and
suggests description rewrites — recommended pattern is **3 eval cases per skill: positive,
negative, edge case**. One third-party source states trigger evals commonly score only ~50%
*because descriptions summarize behavior instead of listing trigger conditions* — this is exactly
the python-conventions failure mode from Context above, independently confirmed as a common,
named failure pattern, not a one-off.

**`/skill-doctor`**: also gated/undocumented — reports per-skill 7-day token usage, invocation
count, context cost, and never-invoked warnings. Usage-monitoring, not trigger-testing; doesn't
address this plan's problem directly.

**Scoping question (does either apply to this repo's bare `.agents/skills/<name>/` layout, not a
packaged plugin)**: still not fully confirmed, but `claude plugin init` can reportedly scaffold a
lightweight `plugin.json` directly into an *existing* skill directory with no marketplace step —
suggesting conversion cost is low if it turns out to be required. Not verified hands-on.

**Community comparison** (real popularity data, not vibes): **promptfoo** (24,464★, actively
maintained) and **DeepEval** (17,779★, pytest-native, active) are both far more popular than
anything Claude-Code-specific, but neither is built for *cold* trigger-routing — both test whether
a model calls the right tool correctly *once given full tool definitions in context* during a live
run (DeepEval's `ToolCorrectnessMetric`/`ArgumentCorrectnessMetric`), which is an adjacent but
different problem from "does the bare description text alone cause selection." Either could be
adapted to simulate cold routing (feed only the description + a battery of prompts, assert the
expected selection), but that means building the harness ourselves on top of a general eval
library, not using an off-the-shelf feature. Anthropic's own "Writing effective tools for AI
agents" engineering-blog guidance is qualitative prose only (avoid jargon, avoid ambiguous
parameter names) — no automated methodology of its own; `skill-creator` is where Anthropic
operationalized that advice into something testable.

## Recommended direction

**Adopt the trigger-eval methodology `skill-creator` uses — 3 cases per skill (positive, negative,
edge case), checked cold (description text only, fresh context, no prior conversation) — as this
repo's actual testing convention**, independent of whether Anthropic's own gated CLI ends up being
the thing that runs it. This is the only candidate actually purpose-built for the specific failure
already observed (python-conventions under-triggering on jargon-only description text), it has
independent third-party validation of that exact failure mode, and it's cheap to implement as a
small in-repo mechanism rather than adopting a general eval framework as a dependency — consistent
with this repo's existing low-boilerplate bias.

Concretely: for each `skills/<name>/SKILL.md`, author 3 short natural-language prompts (one that
should trigger it, one plausible-but-shouldn't, one boundary/edge case) and check — via a fresh
subagent/API call given *only* the skill's `description` frontmatter, not its body — whether it
would correctly decide to invoke that skill for each. Where exactly the prompts live (inline in
each `SKILL.md`'s frontmatter? a sibling `<name>.evals.yaml`? one shared file?), how the cold check
is actually invoked (spawn a bare Task/Agent call with just the description text and the full list
of other skill descriptions, matching real trigger conditions; or a direct Anthropic API call from
a script/pytest test — has a real per-run token cost either way, worth deciding budget/cadence for),
and whether it's wired into `inv ai.skills`, a dedicated `inv` task, or a manually-invoked check are
all still open — implementation-level design, not resolved by this research pass.

**Fallback**, only if the custom in-repo version proves too heavy or the description-only cold-check
harness turns out non-trivial to build well: **promptfoo** over DeepEval — more stars, more mature,
already has function/tool-calling eval primitives to build the cold-routing simulation on top of,
and its YAML test-matrix format is lower-boilerplate than DeepEval's pytest classes even though
DeepEval is pytest-native and this repo already uses pytest.

[NEEDS CLARIFICATION: mechanism for the cold check — a live Agent/Task call each test run (real
token cost, needs a budget/cadence decision — every `inv ai.skills` run? CI only? manual/on-demand
only, matching this repo's stated aversion to auto-triggered mutation/cost) vs. a direct Anthropic
API call from a plain script/pytest test (same cost question, different plumbing) vs. attempting to
actually get `claude plugin eval`/`skill-creator` access via `/feedback` and using Anthropic's own
gated tool once available.]

[NEEDS CLARIFICATION: where do the 3 positive/negative/edge prompts per skill live — inline
frontmatter, a sibling eval file per skill, or one shared corpus file — and does the "cold" check
need to see the *other* skills' descriptions too (to catch cross-skill false positives — the wrong
skill winning instead of the right one), not just a binary yes/no on the one skill in isolation?]

[NEEDS CLARIFICATION: confirm hands-on whether `claude plugin init` can actually convert an existing
bare `.agents/skills/<name>/` directory into something `claude plugin eval`/`skill-creator` can
target, in case Anthropic's own tooling becomes available and preferable to a hand-built harness.]
