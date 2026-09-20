---
status: landed
updated: 2026-09-20
repo: git@github.com:TheodoreAD/power-user-linux-setup.git
---

# The Python version floor rule has no permanent home

## Context

Stated by the user 2026-08-29, in a `repo-tasks` session:

> **3.11 is the floor** for `repo-tasks`, for libraries, and for anything other people may need to
> run on their own machines — skills and MCP servers included. **Applications start on 3.14.**

The axis is who controls the interpreter. An application controls its own runtime and may use
whatever syntax that runtime supports; anything someone else installs into their own project does
not, and 3.11 is where that floor sits.

The rule is currently written down in two plan files and nowhere permanent:

- `ingesta/plans/2026-08-29-python-version-floors.md` — the owning design plan, which records the
  rule as "the rule the household wants" and works out the mechanism.
- `repo-tasks/plans/2026-08-29-python-floor-in-the-shipped-configs.md` — the half that lives in the
  shipped canonical configs.

Both are working-set files that empty out on retirement. The rule outlives them and needs a home
that does not.

## Why here

Checked 2026-08-29: `~/AGENTS.md` contains no rule mentioning Python versions at all — zero hits for
`3.11`, `3.14`, `requires-python`, `python_requires`. So this is a new rule, not a variant, and it
is assessed against `contributing/global-agents-md.md`'s three admission criteria:

1. **States its trigger** — "Setting or changing a Python project's version floor" is a situation,
   not a topic.
2. **Doesn't duplicate an existing rule** — nothing in any fragment covers it.
3. **Evidence goes in `contributing/global-agents-md.md`**, not inline — the measurements below.

Tier placement argues for the always-loaded file rather than a skill: the miss is silent and
expensive. A library published with a 3.14 floor fails for a consumer at install time, on their
machine, not in any gate here. The competing home is `agent-skills`' `python-conventions` skill,
where the family's other Python defaults live — cheaper on always-loaded context, but the floor is
chosen at project _generation_, which is exactly when a Python-authoring skill is least likely to
have loaded.

[DECISION: `~/AGENTS.md` over the `python-conventions` skill, on load-time reliability at the moment
the floor is actually chosen. Revisit if the always-loaded file comes under size pressure — the
admission criteria's own reference points are ≤200 lines and ≤15 rules, and moving a rule out later
needs per-rule user approval anyway.]

Fragment ownership: **this section is out of date and the destination has changed.** It named
`portable.md` (order 30) against `this-setup.md`, on the axis of what a rule depends on. Neither
file exists — the fragments were re-cut by subject on 2026-08-30, and what a rule assumes is now a
label on its heading rather than a choice of file (`contributing/global-agents-md.md`, "Fragments
are subjects, dependency is a label"). So the question is no longer "portable or not" but **which
subject cluster owns a Python version floor**, and the honest answer is that none of the seven is a
clean fit: `research.md` holds "Choosing a tool or library" and "Installing a tool on this machine",
which is the nearest neighbourhood, but a version floor is a project-shape decision rather than a
tool choice.

The wording guidance survives the change and still applies: state it without naming this user's
specific repos — "a project other people install" rather than a list — since the admission criteria
push away from rules that name this setup.

**Settled 2026-09-20: `research.md`, as its own heading.** Its nearest neighbour there, "Designing a
uv tool-install or shared-dependency mechanism", names the same field and was the extension
candidate, but its heading names a different trigger — designing an installer, not choosing a floor
— so the extend-or-split clause makes this a split rather than an extension. The cluster is still
imperfect for the reason above; `research.md` wins because a floor is chosen at the same moment as
the rest of that cluster's decisions, while a project is being designed.

## Evidence for `contributing/global-agents-md.md`

Measured 2026-08-29 in a scratch project, and independently reproducing what `ingesta`'s plan found:

- **ruff infers the floor from `requires-python` when `target-version` is absent.** A file using
  `def identity[T](value: T) -> T` passes under `requires-python = ">=3.12"` and fails under
  `>=3.11`, with the same `ruff.toml`. Only the pyproject line changed.
- **basedpyright does not.** Same tree, `requires-python = ">=3.11"`, same file: 0 errors, 0
  warnings. It validates against the interpreter it finds — 3.14 on this machine.

So a project whose declared floor is 3.11 can be developed entirely on 3.14 with one of its two
static checkers silently agreeing, which is why the rule needs stating rather than being left to the
tools to enforce.

A third measurement, added 2026-08-30 from a `repo-tasks` session, because the skills case below
turns on it:

| invocation                              | version |
| --------------------------------------- | ------- |
| `/usr/bin/python3` (Ubuntu 24.04.4 LTS) | 3.12.3  |
| `python3` from a shell in `repo-tasks`  | 3.11.15 |

[PITFALL: "what does bare `python3` run" has at least three answers on one machine — the distro's
interpreter, whatever venv is active in the directory it was invoked from, and whatever a harness
put on `PATH`. The second row above is not the distro's Python: `repo-tasks`' `.envrc` puts
`.venv/bin` on `PATH`. The first attempt at this measurement returned 3.11.15 and would have been
written down as "Ubuntu 24.04 ships 3.11", which is false. A skill script is invoked from wherever
the agent's session happens to be, so in practice it inherits an unrelated project's venv — any
floor stated for skills has to say which of the three it is a claim about. Same
non-isolated-environment trap as `uv run --with`, hit again in a different tool — that one is now a
rule in `~/AGENTS.md`'s "Reading a command's result", with the measurement in
`contributing/global-agents-md.md` under the same heading.]

## The answers, 2026-09-20

All five were open because the rule had never been worked through as categories. The user did that
on 2026-09-18, in `scaffoldapy`'s `plans/2026-09-18-python-version-tier-rules.md`, which answered
three of them outright; the last two were settled with the user while writing the rule.

**Syntax rule or support statement — both, and the tier says which.** Where a resolver stands
between the code and the interpreter, `requires-python` binds and the declaration _is_ the rule.
Where nothing does — a script meeting an ambient `python3` — there is no field to declare, so the
floor is carried by writing 3.11-compatible code plus a version guard that fails with a sentence
naming the requirement. The two readings were never in competition; they belong to different tiers.

**What enforces it for skills: the repo develops at the floor**, so the ordinary `pytest` run is the
check, with nothing separate to keep alive. Stated as a general rule in the tier plan — _a repo
whose shipped artifacts run on an interpreter it does not choose develops at those artifacts'
floor._ That also disposes of the `requires-python`-as-a-lie-to-ruff idea: developing at the floor
gets a true check without telling the linter anything untrue.

**Per-repo, derived from the artifact**, not per-script. `agent-skills` is its own tier for exactly
this reason rather than being an exception to the library tier.

**The skills reading is in the global rule, compressed** — three lines rather than the tier plan's
four numbered rules. Decided with the user 2026-09-20 on the admission criteria's own tier-placement
clause: the ambient case has no resolver, no declaration and nothing mechanical enforcing it, which
makes its miss silent and expensive, and that is the test for staying in the always-loaded file.

**"Applications start on 3.14" means the newest stable, and the rule carries the number too** — "the
newest stable release, 3.14 today". Decided with the user 2026-09-20. The literal alone goes stale
the year 3.15 ships with nothing to prompt anyone back; the principle alone leaves an agent to look
up what the newest stable is, and guess.

## Recommended direction

1. ~~Add one trigger-named rule to whichever `config/agents-md/` fragment ends up owning it.~~
   **Done 2026-09-20** — `config/agents-md/research.md`, "Setting or changing a Python project's
   version floor", written as a recipe per criterion 4 because the failure is a wrong-shaped output
   (the declaration itself) rather than a discipline lapse.
2. ~~Put the three measurements above in `contributing/global-agents-md.md`.~~ **Done**, under a
   matching heading, with the two 2026-09-18 measurements the tier work added.
3. ~~`inv deploy.all --name agents-md`, then confirm.~~ **Done** — line 662 of the assembled
   `~/.agents/AGENTS.md` and of both copies (`~/.claude/CLAUDE.md`,
   `~/.copilot/copilot-instructions.md`); `inv ai.check-rule-prerequisites` clean.
4. The mechanism that makes a project _declare_ its tier is not this repo's — it belongs to
   `scaffoldapy`, per `ingesta`'s plan. This rule is the statement, not the enforcement. **Still
   open there**, as step 2 of that repo's tier-rules plan.

## Migrated to

- `config/agents-md/research.md` — the rule itself, which is what this plan existed to produce.
- `contributing/global-agents-md.md`, "Setting or changing a Python project's version floor" — the
  axis, the three measurements (including the two this plan did not have), the bare-`python3`
  pitfall, and the three decisions: fragment choice, principle-plus-number, and keeping the ambient
  case in the always-loaded file.

Not migrated: the tier table itself, which is `scaffoldapy`'s
`plans/2026-09-18-python-version-tier-rules.md` and stays there — that repo owns the generation-time
question, and a second copy here would diverge from the one that is kept current.
