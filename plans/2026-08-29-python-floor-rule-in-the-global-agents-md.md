---
status: idea
updated: 2026-08-29
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

Fragment ownership per `config/agents-md/README.md`: this is a convention that holds on any machine
with any agent, so `portable.md` (order 30), not `this-setup.md`. It should be worded without naming
this user's specific repos — "a project other people install" rather than a list — since
`portable.md`'s stated direction is away from rules that name this setup.

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

## Open questions

[NEEDS CLARIFICATION: does the rule mean **write 3.11-compatible syntax** (defensive: the script
runs anywhere, including a 22.04 machine's 3.10, and simply must not use newer syntax) or **declare
`requires-python = ">=3.11"` and stop supporting 22.04** (a support statement)? For a packaged
library the two coincide. For `agent-skills`' stdlib scripts, run as a bare `python3`, they do not,
and they produce different code and different failure modes. The first is unverifiable by any tool
the family runs, since nothing type-checks a bare stdlib script against a version it never runs on;
the second is checkable but has no field to put the declaration in. The distro table that motivated
the question — 3.12 on 24.04, 3.10 on 22.04 — is real but is only the floor for the _system_
reading, not for a script invoked inside an active venv, which is the common case for an agent
session.]

[NEEDS CLARIFICATION: if the floor is a syntax rule, what enforces it for skills? `repo-tasks`'
shipped `ruff.toml` infers its target from `requires-python`, and `agent-skills`' scripts are not a
package, so there is nothing to infer from — measured in `repo-tasks` 2026-08-29: with the field
absent the linter resolves to no version at all and accepts the newest syntax, while the formatter
falls back to 3.10. **A skills repo therefore gets the most permissive linting of anything in the
family**, the exact opposite of what a floor intends. The cheapest fix is a `requires-python` in
that repo purely so ruff has something to infer from — a small lie told to a linter to get a true
check, worth weighing against stating the rule and accepting it is unenforced.]

[NEEDS CLARIFICATION: does the floor apply per-script or per-repo? A skill only ever run by an agent
on this machine has different exposure from one shipped for others to install, and `agent-skills`
holds both kinds.]

[NEEDS CLARIFICATION: does the skills reading belong in this rule's wording in `~/AGENTS.md`, or one
level down in `agent-skills`' own `AGENTS.md`? The global rule could stay short and state the
principle. Against: the ambiguity is in the global sentence itself, and whoever reads that sentence
is the person who needs the answer.]

[NEEDS CLARIFICATION: does "applications start on 3.14" mean the current stable at the time the
project is generated, or the literal number 3.14? The first is what makes the rule survive 2027; the
second is what a generated `requires-python` can actually contain. Probably: the rule says "current
stable", and each project records the number it was generated with.]

## Recommended direction

1. Add one trigger-named rule to `config/agents-md/portable.md`, trigger + rule + one clause of why,
   per that file's shape.
2. Put the three measurements above in `contributing/global-agents-md.md` under a matching heading.
3. `inv deploy.all --name agents-md`, then confirm the deployed `~/AGENTS.md` carries it.
4. The mechanism that makes a project _declare_ its tier is not this repo's — it belongs to
   `scaffoldapy`, per `ingesta`'s plan. This rule is the statement, not the enforcement.
