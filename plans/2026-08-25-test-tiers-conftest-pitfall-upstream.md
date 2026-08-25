---
status: idea
updated: 2026-08-25
depends_on: [repo-tasks]
---

# Record the second-`conftest.py` pitfall where the family convention lives

## Context

Surfaced while retiring `plans/2026-08-24-adopt-test-tier-structure.md` (2026-08-25). That plan
carried a `[PITFALL:]` hit for real in `scaffoldapy` when it took the two-tier split: with a
tier-local `tests/integration/conftest.py` present, an import from `conftest` resolves to a
_different file per tier_ — `tests/conftest.py` from the unit tier, the tier-local one from the
integration tier, where it raises `ImportError`. Silent and direction-dependent. Shared constants
that feed `@pytest.mark.parametrize` cannot be fixtures, so they need a distinctly-named module
(`scaffoldapy` used `tests/support.py`), never `conftest.py`.

The pitfall was migrated into this repo's `tests/README.md`, conditionally ("if this repo ever grows
an integration tier"). That is the wrong primary home: the two-tier layout is a family convention
owned by `repo-tasks` and shipped to every consumer, and its writeup —
`repo-tasks/contributing/test-tiers.md`, "Conftest layout" section — documents the three-conftest
arrangement without this trap. Every consumer that adopts the split with a second `conftest.py` is
exposed, and only the two repos that already hit it know.

Not done during the retirement because it is a cross-repo edit (`~/AGENTS.md`, "Running a command
against a different repo than the session's project" — substantial work in another repo belongs in
its own session), and a plan is the mechanism for not losing it across that boundary.

## Open questions

[NEEDS CLARIFICATION: does `repo-tasks`' own layout already avoid the trap by construction —
`tests/unit/conftest.py` and `tests/integration/conftest.py` both exist there, so does anything in
its integration tier import from `conftest` by module name, or do its tiers only ever consume
fixtures by injection? If the latter, the doc should say that is the rule, not just describe the
files.]

[NEEDS CLARIFICATION: is this worth a `scaffoldapy` template change too — stamping a
`tests/support.py` (or naming it in the generated `tests/README.md`) so a generated repo starts on
the right side of the line — or is a sentence in `test-tiers.md` enough?]

## Recommended direction

One short paragraph in `repo-tasks/contributing/test-tiers.md`'s "Conftest layout" section, stated
as a rule with the `scaffoldapy` incident as evidence: shared parametrize inputs go in a
distinctly-named support module; `conftest.py` holds fixtures only, and nothing imports from it by
name. Then trim this repo's `tests/README.md` copy to a one-line pointer at that section. Do it from
a `repo-tasks` session, running that repo's own gate before committing.
