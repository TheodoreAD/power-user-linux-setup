---
status: landed
updated: 2026-09-28
source_repo: github.com-personal/repo-tasks
source_session: a9904181-df08-4eb5-945e-8aab9336d457.jsonl
source_moment: 2026-09-26
source_plan: plans/2026-08-25-consumer-transitions.md
---

# This repo has no caller for `repo-tasks`' reusable security workflow, and is the only consumer that was never told

## Context

Filed from a `repo-tasks` session on 2026-09-26. Nothing was written to this tree — the measurement
is read-only, taken from outside the repo.

`repo-tasks` ships `.github/workflows/security-reusable.yml` so the family's dependency audit is
defined once and called from each repo in about six lines. **This repo calls it from nowhere.**
Measured by content across all five of its workflows — `ci.yml`, `devcontainer.yml`,
`install-smoke.yml`, `publish_on_push.yml`, `quality.yml` — not by looking for a `security.yml`,
because letting a filename stand in for what it usually holds is the mistake that mis-measured this
family three times.

**Why this is worth a filing rather than a line in the next sweep's notes: this is the most-swept
consumer in the family and it looked finished.** `repo-tasks`'
`plans/2026-08-25-consumer-transitions.md` records two full sweeps of this repo, 2026-09-05 and
2026-09-10, each closing every item then measurable, and `inv consumers.diff` reports it clean on
every other line today — configs current, dev group current, no bootstrap script to pin because it
takes `repo-tasks` through its own lock. The caller was on that plan's "complement list": the items
no `configs.diff` can see because they are not a file it compares. Nothing read that list, so
nothing ever looked.

That changed the same day this was filed — `consumers.diff` now reports the caller and the bootstrap
pin — which is how this was found at all.

## Evidence

Where the family stands, measured 2026-09-26 from `repo-tasks` with `inv consumers.diff`:

| consumer       | caller                                                      |
| -------------- | ----------------------------------------------------------- |
| **this repo**  | **none** — five workflows, not one calls it                 |
| `scaffoldapy`  | present, pinned `d17c607`, current                          |
| `agent-skills` | none — filed there, and its own sweep plan already names it |
| `ingesta`      | present, pinned `d17c607`, **copied from the template**     |
| `invoke-stubs` | no `.github/` at all, so the question there is upstream     |

`repo-tasks` itself calls its own copy by relative path and is done.

**The two that have one got it from `scaffoldapy`'s template**, which is why this repo and
`agent-skills` are what is left: neither was generated from it, so the leverage that covered the
other two cannot reach either.

## Recommended direction

Add `.github/workflows/security.yml`, whose one meaningful line is a **job-level** `uses:` naming
`TheodoreAD/repo-tasks/.github/workflows/security-reusable.yml` at a full 40-character SHA, with the
readable version in a trailing comment. `scaffoldapy`'s and `ingesta`'s copies are the reference;
both pin `d17c607`.

Two things to know before pinning:

- **`d17c607` is current, and that is an accident rather than maintenance.** It is still the only
  commit ever to have touched `security-reusable.yml`. So copying either existing caller verbatim is
  correct today, and the first edit upstream makes every caller stale at once — silently, except
  that `repo-tasks`' `inv consumers.diff` now compares each pin against that file's newest commit
  and says so.
- **This repo installs `actionlint`, `zizmor` and friends onto `PATH` machine-wide**, which is
  exactly the masking `repo-tasks`' sweep doc warns about: a workflow that lints clean here can
  still fail in CI, where only the declared group exists. Worth a real CI run rather than a local
  `inv
  quality.workflow-check` before calling it done.

[DECISION: its own `security.yml`, not a job in `quality.yml`. This repo's `AGENTS.md` makes family
convergence strict: one identical composite in every consumer, and every other consumer uses a
separate file. There is also a reason specific to this repo: `quality.yml` is what `publish-stable`
requires before moving the `stable` tag, and an OSV advisory landing upstream should not block a
release of unchanged code. Settled 2026-09-28.]

[DECISION: nothing to install. The reusable workflow sets up uv itself and runs `uv audit --locked`
against `uv.lock`, so neither `setup.toml` nor a dependency group has to provide anything. Checked
2026-09-28.]

## Migrated to

- **The caller**: `.github/workflows/security.yml`, `dfb5792`, pinned `d17c607`. Its header comment
  carries both decisions above. The first real run, 36353514913 on `97cdd4c`, passed: the audit job
  finished in 43s.
- **The masking risk named above** (tools on `PATH` machine-wide): answered by that CI run, not by
  the local gate.
