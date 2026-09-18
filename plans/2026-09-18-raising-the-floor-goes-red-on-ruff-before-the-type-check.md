---
status: landed
updated: 2026-09-19
source_repo: github.com-personal/repo-tasks
source_moment: 2026-09-18T18:35:49+03:00
source_plan:
---

# What step 2 of the UV_PYTHON plan will actually hit, and it is not the type check

An addendum to `plans/2026-09-18-replace-uv-python-with-a-uv-managed-default.md`, absorbed into this
repo earlier today. Filed rather than added to it because this session no longer may edit that file
— it is in this repo's tree now, not the store.

## The gap

That plan's step 2 is:

> **Fix this repo's own declaration** to `requires-python = ">=3.14"`, matching the pin it already
> has and the tier it is in.

It reads as a one-line edit, and the plan gives no reason to expect otherwise. **It is a floor
_raise_, and a floor raise has a consequence the whole rest of that plan does not prepare you for.**

Everything else in this family's interpreter work concerns a floor being _checked_ — a type checker
moved down to the declared floor, finding syntax above it. That is what
`repo-tasks/plans/2026-08-25-consumer-transitions.md` records three times over (`typing.override`
under a declared 3.11), and it is what the six per-repo plans filed today all warn about. A raise is
the other direction and it lands somewhere else entirely.

## The evidence, from the one consumer that has already done it

`ingesta` raised its floor to `>=3.14` during its 2026-09-13 sweep — the same tier decision, for the
same reason. Recorded in `2026-09-13-ingesta-sweep-scored.md`, filed for `repo-tasks` and awaiting
absorption there:

> **Unpredicted, and general to any consumer that raises its floor during a sweep.** The pulled
> `ruff.toml` reads the floor from `requires-python`, so a raised floor turns on the syntax-upgrade
> rules at the same moment: `UP047` flagged two generic functions written with a `TypeVar`, `UP043`
> removed a redundant `AsyncGenerator` default, and the formatter dropped the parentheses from a
> multi-exception `except` (PEP 758, 3.14). **The gate goes red on lint rather than on the type
> check.**

The mechanism is this family's own design working as intended: `949607c` deleted `target-version`
from the shipped `ruff.toml` precisely so each consumer's `requires-python` decides its ruff floor.
Raise the declaration and ruff's target moves with it in the same commit, before any type checker
has an opinion.

[PITFALL: **the two predictions point at different tools, and the one everybody has been rehearsing
is the wrong one here.** A session that has read the interpreter plans expects the type check to
fail and will read a red `ruff check` as an unrelated breakage — most likely reverting the
declaration, which is the one change that was correct. `UP047`/`UP043` fire on code that is not
wrong; they are upgrades newly available at the raised floor.]

## Recommended direction

Do step 2 as its own commit with the lint fixes it causes, not folded into the mechanism swap:

1. Edit `requires-python` to `>=3.14`.
2. Run the gate and expect `ruff check --fix` to rewrite generics and defaults. Read the diff — the
   rewrites are upgrades, and the formatter's PEP 758 `except` change is cosmetic but real.
3. Only then the type check, which should have nothing to say: this repo already develops on 3.14,
   so nothing here has ever run below the new floor.

The size is unknown for this repo and worth a dry run before budgeting — `ingesta` is a different
codebase and its count says nothing about this one.

## What happened, 2026-09-19

**The prediction held exactly and undershot by one tool.** 18 lint findings, 12 auto-fixed, 6
needing the unsafe fix and made by hand; the type check had nothing to say, as this plan said it
would. `UP047` fired on the same shape it fired on in `ingesta` (a `TypeVar`-spelled generic), and
`UP040` on the recursive `TypeAlias` pair.

What this plan did not predict, and the reason the commit is larger than "the lint fixes it causes":

- **basedpyright does not follow `requires-python` on its own.** `pyrightconfig.json` carries a
  literal `pythonVersion` that `inv configs.pull` derives from the field, so between the edit and
  the pull the two checkers contradict each other in a way that reads as nonsense rather than as
  staleness. The pull's diff here was that one line and nothing else.
- **`ruff format` rewrote four multi-exception `except` clauses to PEP 758's unparenthesized form,
  which is a SyntaxError on 3.12.** Three were in `tasks/netdoctor.py`, whose floor is the distro's,
  and its existing parse guard failed loudly. The fourth was in `tests/containers/fakecorp.py`,
  which is invoked as a bare `python3` inside a container, had no guard, and would have shipped
  broken. That asymmetry is the finding: the linter's suggestions are refusable and visible, the
  formatter's are neither.

So the shape generalizes past this plan's own subject — "read the auto-fixes as a diff" is not
enough, because the formatter's changes are not findings and appear in no output.

## Migrated to

- `contributing/quality-tooling.md`, new section "Raising `requires-python` is a ruff change before
  it is anything else" — the measurement, both pitfalls, and the order of operations that works.
- `tasks/netdoctor.py`'s module docstring — why that file is formatter-hostile and what to do when a
  formatter diff appears in it.
- `tests/unit/test_foreign_python_floor.py` — the guard itself, generalized from netdoctor to every
  script this repo runs on an interpreter it does not choose, with the incident in its docstring.

Not migrated: the `ingesta` quotation and the `949607c` reference, which are evidence for a claim
the rationale page now states in its own terms with this repo's own numbers.
