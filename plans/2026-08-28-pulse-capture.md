---
status: idea
updated: 2026-08-28
depends_on: [agent-skills]
---

## Context

Split out of `plans/2026-08-23-cross-repo-skill-feedback-capture.md` on 2026-08-28, which now lives
in [`agent-skills`](https://github.com/TheodoreAD/agent-skills) as
`plans/2026-08-23-cross-repo-skill-feedback-capture.md`. That plan designs the loop — how a problem
with a skill or an `~/AGENTS.md` rule, found while working in some unrelated repo, gets reported
back carrying real evidence instead of a paraphrase. Two pieces of it are PULSE's rather than the
convention's, and they are what this file holds:

- **the routing rule in `~/AGENTS.md`**, because this repo assembles that file from the
  `config/agents-md/` fragments, and
- **`pulse-capture`**, a `wrapper-script` package that does the fiddly parts so a foreign session
  does not have to.

The split happened because the skills moved out. When the design was written, "capture" had exactly
one destination and the tool could hardcode it; now a skill problem lands in `agent-skills` and an
`~/AGENTS.md` problem lands here, so the tool needs a destination and the routing rule needs to name
one. Everything about _what a capture contains_ — the provenance frontmatter, the `## Evidence`
section, the lane boundaries — is a `plan-docs`/`session-harvest` concern and stays with the design
plan in `agent-skills`.

Nothing here is buildable until that plan settles its own open questions; this file exists so the
PULSE-side work has a home rather than being buried in a plan another repo owns.

## The routing rule — `config/agents-md/`, not a skill description

The rule has to fire in a repo that has nothing to do with this one, on a session that may never
load any skill. `agent-skills`' `plans/2026-08-22-skill-trigger-quality-review.md` establishes that
skill `description` matching is the weak link in this family, so the trigger cannot be a skill
description. A short section in the fragments — always loaded, everywhere — states: when you hit a
problem with a skill or a global rule from another repo, don't fix it in place; run the capture
procedure, invoked **by name** so it never depends on description matching.

What changed with the skills move: the rule can no longer say "these are owned by
`power-user-linux-setup`". It has to route — a skill problem to `agent-skills`, an `~/AGENTS.md` or
PULSE-mechanism problem to here — which is one more sentence, and it is the sentence that makes the
tool's destination argument meaningful.

Which fragment it joins is a real question. `portable.md` reaches every agent everywhere but names
two specific repos, which is exactly the machine-specific content that fragment exists to keep out;
`this-setup.md` is the honest home and is only true for this machine. See
`plans/2026-08-26-agent-artifact-authoring-decoupling.md` D9 for the portable/machine split this has
to respect.

## `pulse-capture` — the artifact

A `method = "wrapper-script"` package (`config/pulse-capture.sh` → `~/.local/bin/pulse-capture`,
same shape as the existing `[packages.pulse-proxy-start]`). Runnable from any cwd: no `cd`, no
invoke task discovery, no venv resolution, and a single stable command prefix for the allowlist.

It resolves the transcript path from `CLAUDE_CODE_SESSION_ID` + the cwd slug, locates the
destination repo, writes the skeleton plan file with frontmatter filled in, and prints the path plus
a ready-made commit command. The agent then fills in `## Evidence` and `## Context` with its own
editing tool.

**Why a script rather than "the agent writes the file":** slug computation, session-id resolution
and repo location are exactly the fiddly, silently-wrong-able steps an agent should not re-derive in
a foreign repo. The pilot below is direct evidence — an agent with every reason to do better
paraphrased the incident instead of pointing at the transcript, which is the one thing the design
exists to prevent.

### Facts on this machine it depends on (verified 2026-08-23)

- `CLAUDE_CODE_SESSION_ID` is exported into the Bash tool's environment, so a session can name its
  own transcript without guessing.
- The transcript path is deterministic: `~/.claude/projects/<cwd-slug>/<session-id>.jsonl`, where
  `<cwd-slug>` is the absolute cwd with `/` and `.` replaced by `-`. Confirmed by grepping a live
  conversation's own text and landing on exactly that file.
- `~/.claude/settings.json` sets `"cleanupPeriodDays": 365`, so a cited transcript survives long
  enough to be worth citing. The default is 30 — this is a real dependency, and a machine that has
  not raised it makes every stored pointer expire in a month.
- `pulse-proxy-start` (`method = "wrapper-script"`) is the existing precedent for a `pulse-*` helper
  deployed to `~/.local/bin` from this repo.

### The commit prompt is part of the tool, not a habit

Decided 2026-08-23: writing the file and offering to land it are one continuous step, and the tool
prints the exact `git -C <repo> add/commit/push` sequence so the offer is a single copyable action
rather than three prompts — and so the foreign session never constructs repo-relative paths itself.

The reason it has to be immediate is pollution of a working tree the session does not own. An
uncommitted plan file sitting in another repo is exactly the "unexplained state" `~/AGENTS.md` warns
about: another live session sees an untracked file it did not create and has to decide whether it is
a leftover, a stray output, or real work. A capture that lands within seconds never creates the
ambiguity. Declining is normal and leaves the file in place; it is not a failure path.

Two properties of the printed sequence, both load-bearing: it stages the one path rather than `-A`,
so it cannot pick up churn already in that tree, and it pushes rather than only committing, since a
local-only commit is still invisible to a session on another machine.

### What the pilot corrected about the rationale (2026-08-23)

The traps `pulse-capture` is designed to dodge are real but narrower than the original design
assumed. `git -C`, `dprint --config`, `ruff --config`, `basedpyright --project` and an absolute-path
`pytest` all worked fine from a foreign cwd with no `cd`; only `inv` genuinely needed one, because
task discovery walks up from cwd. That **strengthens** the runnable-from-any-cwd requirement — it is
what makes the script usable at all — and **weakens** the broader "don't touch another repo" framing
it was justified with. See `contributing/global-agents-md.md` ("Running a command against a
different repo than the session's project") for the full exercised list.

## Open questions

[NEEDS CLARIFICATION: is `CLAUDE_CODE_SESSION_ID` set in every session type, or only in the
background-job session where it was observed? Needs a check from a plain interactive session and
from a subagent before the helper can depend on it. Fallback if not: newest `*.jsonl` in the
cwd-slug directory, or a grep for a distinctive phrase from the conversation across
`~/.claude/projects/`. This is the cheapest open question in either plan and it blocks the script.]

[NEEDS CLARIFICATION: how does the tool learn its destination — an explicit argument the agent
passes, or inference from what the friction was about? An argument is unambiguous and puts the
routing decision where the routing rule already states it; inference means the script re-implements
a judgment the `~/AGENTS.md` rule just made. Lean argument, with the rule telling the agent which
value to pass. Either way it can no longer default to `power-user-linux-setup`.]

[NEEDS CLARIFICATION: which `config/agents-md/` fragment carries the routing rule, given it names
two specific repos? See "The routing rule" above — `this-setup.md` is the honest answer and costs
reach; `portable.md` has the reach and would be the first machine-specific content admitted to it.]

## Recommended direction

Sequence, and the first two steps are free:

1. Resolve the `CLAUDE_CODE_SESSION_ID` question — one interactive session, one subagent.
2. Write the `config/agents-md/` routing rule. Docs only, no code, usable by hand immediately, and
   it is what makes the by-hand version of the loop real.
3. Let `agent-skills`' design plan settle the provenance fields and the lane bound, and pilot the
   whole thing by hand on the next real cross-repo friction — `~/AGENTS.md` "Pilot before
   generalizing".
4. Only then `config/pulse-capture.sh` + `[packages.pulse-capture]` + a test, once the by-hand shape
   has survived a real use and the destination question has an answer.

Do not build the script first. The pilot already showed the by-hand version works and that its one
real failure was a missing evidence pointer, which is a content problem the design plan owns — not
something a script existing sooner would have fixed.
