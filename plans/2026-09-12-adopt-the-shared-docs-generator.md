---
status: idea
updated: 2026-09-12
source_repo: github.com-personal/repo-tasks
source_session: db005386-041e-4f80-acbe-6e944677e6fa.jsonl
source_moment: 2026-09-09T21:08:26Z
source_plan: plans/2026-09-01-docs-generation-in-precommit.md
---

# The shared docs generator exists now, and adopting it needs a contract this repo is the test for

## Context

`repo-tasks` landed the mechanism this repo asked for on 2026-09-12 (`5ed82c5`): `inv docs.generate`
renders blocks into their marked regions **first in `quality.fix`**, ahead of the linters and
formatters, and `inv docs.generate-check` sits in `quality.check` and fails the gate when a block
has drifted. Both are in the shared chain, so this repo gets them on its next `repo_tasks` bump
whether or not it uses them.

It was proved against a block rendered from `repo-tasks`' own code — a table of every task needing
network, Docker or an authenticated `gh` — and the ordering did what this repo's own experience
predicted it would: a second `inv quality.fix` run changes nothing, with **no pre-padding anywhere
in the renderer**.

**What is in it for this repo is deleting two workarounds, not gaining a feature.** Both are
load-bearing today and both are recorded in `tasks/devcontainer.py`:

- `util.markdown_table` pre-pads to dprint's own GFM table style, "which is what keeps this block a
  fixed point of `inv quality.fix` rather than something dprint and render-docs rewrite past each
  other forever". That padding has a second consumer in `tasks/catalog.py`, so it is a shared
  workaround rather than a local one.
- `_generated_content()` pre-wraps its prose paragraph at `dprint.json`'s markdown `lineWidth` (100)
  for the same reason — and the comment records that the paragraph did **not** have that treatment
  originally, so the block was stale in git the whole time and no run could settle it. Found
  2026-09-01 by the drift test, on its first execution.

Under the shared mechanism neither is needed for the table: the generator runs before the formatter,
and both halves compare with formatter-owned layout normalized away.

## Evidence

The blocking question, quoted from the filing repo's plan
(`plans/2026-09-01-docs-generation-in-precommit.md`, still open there):

> what is the generator contract **for a consumer's own generator**? This is the one question the
> landed mechanism does not answer: it covers blocks rendered from _this package's_ code, where the
> renderer ships alongside the chain that calls it.

This repo has **three** generators, all in its own namespace, which is exactly what makes it the
test case: `inv devcontainer.render-docs` (`tasks/devcontainer.py:77`), `inv screenshot.render-docs`
(`tasks/screenshot.py:326`), and the catalog blocks written through `util.ensure_block` in
`tasks/catalog.py:147`. A `repo-tasks` task composed in `quality.py` cannot see any of them: `pre=`
chains are built in that package, and nothing hands it the consumer's root collection.

[PITFALL: **the filing plan claimed this repo has "no automatic drift protection at all", and that
is wrong.** Three drift tests already assert that each generated block matches its source —
`tests/unit/test_devcontainer.py:246`, `tests/unit/test_screenshot.py:53`, and
`tests/unit/test_catalog.py`. The claim dates from the CI auto-commit job being deleted on
2026-09-01 and was already false by the time it was written; the tests are what caught the stale
prose block that same day. Do not add a fourth as "interim cover" — the interim already has cover,
and that changes the urgency of this plan from "restore a missing check" to "delete two
workarounds".]

## Open questions

~~How does the shared chain reach a generator that lives here?~~ **Settled and landed in
`repo-tasks` the same day (`5585877`), before this plan was filed for long enough to be read.**
Declare the commands in `repo-tasks.toml`:

```toml
[docs]
generators = ["inv devcontainer.render-docs", "inv screenshot.render-docs"]
```

`docs.generate` runs them after its own blocks, first in `quality.fix`. Commands rather than task
names because reaching a task here means a subprocess either way — a task composed in that package
cannot see this repo's namespace — so a task name would only add a restriction and an existence
question. Each command must be deterministic and offline, the rule every gate step follows.

**There is deliberately no check-half counterpart**, which is why the three drift tests below stay:
a generator writes, so running it from `quality.check` would break that half's read-only contract,
and a unit test asserting the block matches its source already runs in the unit tier that gate
includes.

So nothing blocks this repo any more. What is left is the adoption itself, and the one requirement
it puts back on the shared mechanism — the prose question below.

[NEEDS CLARIFICATION: does the prose paragraph survive the shared comparison? **Probably not as
written.** `repo-tasks`' `docs._normalized` collapses internal whitespace and dash runs **per
line**, which covers a table whose alignment the formatter owns — but a paragraph that dprint
re-wraps to width 100 changes its _line breaks_, and a line-by-line comparison sees that as a
difference. So adopting the mechanism for `_generated_content()` needs either the pre-wrapping kept,
or the shared comparison made paragraph-aware (split on blank lines, collapse whitespace within a
paragraph). That is a requirement this repo puts on the shared mechanism, and it is the kind of
thing that is cheap while the mechanism has one consumer and expensive later.]

## Recommended direction

1. ~~Settle the contract in `repo-tasks` first.~~ Done — `[docs] generators`, above. Bump this
   repo's `repo_tasks` pin far enough to have it, then declare the two `render-docs` commands and
   run `inv quality.fix` twice, diffing in between: the second run changing nothing is the whole
   acceptance test.
2. **Take the table before the prose.** The table is what the shared comparison already handles, and
   deleting `util.markdown_table`'s padding is the measurable win — both its consumers should stay
   stable across two `inv quality.fix` runs afterwards, which is the same check `repo-tasks` used on
   itself.
3. **Keep the drift tests.** They are cheaper than the gate step and they fail with a message naming
   the task to run; the shared check half is a second line of defence, not a replacement.
4. Bump `repo_tasks` in this repo's lock in the ordinary sweep rather than for this — the new tasks
   arrive either way and no-op here until a file carries the markers.
