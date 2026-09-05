---
status: idea
updated: 2026-09-05
source_repo: github.com-personal/repo-tasks
source_session: 86b6d25d-eb68-4751-b989-ad45931ef62a.jsonl
source_moment: 2026-09-05T11:06:17Z
---

# The rule of least surprise is not in `~/AGENTS.md`, and the user believes it is

## Context

Correcting a design in `repo-tasks` on 2026-09-05, the user wrote, verbatim:

> the point is the rule of least surprise for users. **i'm sure i've mentioned this is important in
> our projects.**

`rg -in 'least surprise|principle of least|surprising' ~/AGENTS.md` returns nothing. The belief is
reasonable — the principle is _applied_ in one place, "Adding a CLI flag" — but it is nowhere stated
as the general rule, so nothing carried it to the case that actually went wrong.

**The user having to say it is the finding.** This is the shape the always-loaded file exists for: a
session had already shipped and pushed the surprising design, gate green and CI green, and nothing
would have surfaced it.

## What it cost, concretely

A session added agent-friendly folded output to `repo-tasks`' quality gate: eleven gate steps
captured, one status line each, output folded on success. It measured well and it was wrong in three
ways, all the same way —

- it changed the default for **every consumer** on upgrade, none of whom asked;
- it reached eleven of ~90 `c.run` call sites, so two output shapes coexisted in one tool;
- it turned invoke's `UnexpectedExit` into `Exit` unconditionally.

The redesign inverted the switch — stock invoke by default, reporting behind `REPO_TASKS_RUN_REPORT`
— and the whole of that work (a new module, a switchover, a docs rewrite, three commits) was the
cost of the missing rule. Four commits landed and were pushed before the correction; the correction
is `repo-tasks` `d322392`..`7db8b29`.

The reconciliation is worth recording alongside the rule, because it is what makes the rule cheap to
follow rather than a tax: the measurement that argued for changing the default (58% of gate runs
piped) was entirely **agent** sessions, and agent shells already get a `CLAUDECODE`-guarded profile,
so the departure can be switched on for exactly the population that needed it without touching
anyone else's default. "Flip the default" and "reach the population" looked like the same lever and
were not.

## Recommended direction

**Extend `config/agents-md/research.md`'s existing "Adding a CLI flag" section — do not add a
40th.** That section already states this principle for one case ("prompt on by default, `-y`/`--yes`
to skip — never an opt-in `--confirm`", "no hacks that complicate the mental model"); what is
missing is the general form and the case it does not currently reach — changing what a **library or
wrapped tool does by default**, where there is no flag to shape and the surprise is the behaviour
itself.

Draft, to append to that section:

> The same principle beyond flags: **when you change what a tool already does, the documented
> behaviour stays the default and the departure is opt-in** — most sharply when the tool is a shared
> dependency, where "default" means every consumer's next upgrade. A change that only some call
> sites get is worse than either choice made whole, because the tool then has two behaviours and no
> rule saying which applies. If the departure has an audience that genuinely needs it by default,
> reach that audience through their environment rather than by moving the default under everyone
> else.

[DECISION: extend rather than add, on the file's own admission criteria. `~/AGENTS.md` stands at
**39 rules / 770 lines** (re-counted 2026-09-05 evening, after `5d69b8a`, `a12391d` and `9101808`;
the count was 756 lines when this was first written and the rule count did not move), well over its
own ≤15/≤200 reference points, so a new heading costs context in every session in every repo.
Extending leaves the rule count unchanged and puts the general form next to the instance a reader
already has. The tier test still says always-loaded rather than a skill: the miss is **silent** —
the surprising design passes its gate, passes CI, and reads as finished — and it is **expensive**, a
full redesign of pushed work here.]

[NEEDS CLARIFICATION: whether "Adding a CLI flag" should be retitled now that it would cover more
than flags — something like "Adding a flag, or changing what a tool does by default". Against:
renaming a section breaks any citation of it elsewhere in the corpus, and `contributing/` pages do
cite these by name. For: the current title is what would stop a reader finding the general rule,
which is the entire defect being fixed. Check inbound citations before deciding.]

[DEFERRED: whether the same principle wants a line in `contributing/global-agents-md.md`'s own
admission criteria — "a rule the user believes is already recorded" is arguably direct evidence for
admission, and the criteria do not currently name that signal. Filed as an observation, not a
proposal; it is that document's call.]

## Evidence

- The user's turn, 2026-09-05T11:06:17Z, in transcript `86b6d25d-eb68-4751-b989-ad45931ef62a.jsonl`.
  The distinctive phrase to search for is _"without the env var, everything runs normally"_.
- The full design and its decisions: `repo-tasks`
  `plans/2026-09-05-run-reporting-as-an-opt-in-agent-mode.md` and `contributing/quality-gate.md`,
  "What the gate prints".
- The absence: `rg -in 'least surprise|principle of least|surprising' ~/AGENTS.md` → no matches, on
  2026-09-05, re-checked the same evening after that day's `agents-md` commits.
- The target section survives those commits: `config/agents-md/research.md` still carries "Adding a
  CLI flag", and the fragments and the deployed file agree at 39 rules, so the deploy is current and
  this recommendation can be applied as written.
