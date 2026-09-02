---
status: idea
updated: 2026-09-02
---

# Dry-run branches that re-derive a check the write path already owns

## Context

Carried out of `plans/2026-08-30-dry-run-reports-agents-md-missing.md` at its retirement
(2026-09-02), where both questions below were opened and neither blocked the defect's fix.

That defect: `_install_wrapper_script`'s `if util.DRY_RUN:` branch decided whether a package was
`ok` by checking every `symlink_dest`, while the writer it stands in for — and `verify.py`'s
`_symlink_checks` — both skip a link whose parent directory is absent, because a missing `~/.codex/`
means that agent is not installed. So the dry run reported `agents-md` MISSING on a machine where
`deploy.status` said `ok` and the deployed file was correct.

**The interesting part is that it drifted from two independent implementations of the same rule at
the same time**, which is what makes this a pattern question rather than a bug report. Both of the
others state the rule in a docstring; the dry-run branch stated it nowhere and simply did something
else.

## Open questions

[NEEDS CLARIFICATION: **how many other `if util.DRY_RUN:` blocks re-derive a condition the write
path owns?** Cheap to enumerate — `rg -n 'if util.DRY_RUN' tasks/` and read each one for whether it
calls the same helper the writer calls or reimplements the test. The answer decides whether this is
one stale branch or a shape worth a convention, and the convention would be cheap to state: a dry
run reports on the writer's own predicate, never on its own copy of it.]

[NEEDS CLARIFICATION: **is one `ok`/`MISSING` word the right report at all?** A wrapper-script
package can be wrong in three separable ways — content not deployed, content stale, a link pointing
somewhere else — and one word for all three is what made the original symptom ambiguous enough to
need investigating. `deploy.status` already distinguishes the content states, so the dry run could
defer to it rather than compute a verdict. The constraint on any change here: `phases.py`'s "already
looks complete" probe greps this output for the literal `MISSING`, and `tests/unit/test_tools.py`
pins that, so the label is an interface rather than a message.]

[NEEDS CLARIFICATION: is there a test shape that would have caught the original drift on the commit
that introduced it? The fix's own test asserts one case; what it does not do is assert that the dry
run and the writer agree in general. A property-style test over a small matrix of link states —
parent absent, link missing, link correct, link pointing elsewhere — would, and would keep agreeing
as either side changes.]

## Recommended direction

Enumerate first, decide after. The first question is a single `rg` and a read of each hit, and its
answer is what says whether the other two are worth spending anything on: one stale branch needs no
convention, and four need one.

Do not start from the reporting-shape question. It is the more interesting one and it changes an
output another module greps for, so it wants evidence about how often the ambiguity actually costs
something — which the enumeration supplies.
