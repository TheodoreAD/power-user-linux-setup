---
status: idea
updated: 2026-08-26
depends_on: [repo-tasks, scaffoldapy]
---

# Retrofit the three built `*-polite-mcp` repos onto the family conventions

## Context

Inherited from the now-retired `plans/2026-08-14-python-repo-scaffolding.md`, whose §A–§F all
landed: `repo-tasks` exists and is a real dependency, `scaffoldapy` generates new repos onto it,
`repo_tasks.configs` distributes the canonical tool config, and `contributing/`'s
[`repo-family-architecture.md`](../contributing/repo-family-architecture.md) and
[`quality-tooling.md`](../contributing/quality-tooling.md) hold the reasoning. This is the one piece
of that plan that never executed.

`olx-polite-mcp`, `temu-polite-mcp` and `freshful-polite-mcp` predate all of it. They carry
hand-duplicated leaf tasks in their own `tasks.py` rather than `repo_tasks.ns`, a flat package
layout rather than `src/`, and no `configs.pull` relationship at all — so every improvement made to
the shared baseline since has reached every repo in the family except these three. That is precisely
the drift the whole effort existed to stop, still running in the three oldest repos.

As of the last audit recorded in that plan:

| repo                  | `.envrc` | Claude direnv hook | `tasks.py` on `repo_tasks.ns`       | `dprint.json` |
| --------------------- | -------- | ------------------ | ----------------------------------- | ------------- |
| `olx-polite-mcp`      | yes      | yes                | **no — hand-duplicated leaf tasks** | yes           |
| `temu-polite-mcp`     | no       | no                 | **no — hand-duplicated leaf tasks** | yes           |
| `freshful-polite-mcp` | no       | no                 | **no — hand-duplicated leaf tasks** | yes           |

`emag-polite-mcp` and `altex-polite-mcp` are still plan-only and need no retrofit — they pick up the
template with `repo-tasks` from the start whenever their implementation begins.

**Why it was deferred**, by direct instruction on 2026-08-19: `scaffoldapy` needed real fresh-repo
generation mileage before `copier update` got pointed at an already-existing, already-diverged repo.
Not abandoned — required eventually, per the "no per-repo allowances" decision that governs this
family. The retiring plan's own closing note judged that condition "plausibly satisfied now, given
§A/§B/§D/§E/§F have all since landed and been exercised for real, but not yet revisited."

## Open questions

[NEEDS CLARIFICATION: Has `scaffoldapy` accumulated enough fresh-generation mileage to lift the
deferral? The condition was stated qualitatively, so answering it means looking at what has actually
been generated with it since 2026-08-19 and whether anything about the template still moves week to
week. If it has stabilized, this plan is unblocked and promotes to `planned`; if not, it stays
parked and this question is the thing to re-ask.]

[NEEDS CLARIFICATION: Is `copier update` the right mechanism against a repo that was never generated
from the template? Copier's update flow is built for a repo that has an `.copier-answers.yml` and a
recorded source commit. Retrofitting means manufacturing that starting point — `copier copy` with
`--pretend`-style review, or answering the questionnaire against the existing layout and accepting a
large first diff. Worth one hands-on trial against the least-diverged repo (`olx-polite-mcp`, which
already has `.envrc` and the Claude hook) before committing all three to a procedure.]

[NEEDS CLARIFICATION: Do `core/`'s politeness/cache/fetch primitives belong in `repo-tasks`? Still
genuinely open from the retired plan. Today they live in `olx-polite-mcp/core/`. The restraint that
repo's own `AGENTS.md` applies to its Playwright fetch path — "generalize only once a second site
actually needs it" — probably applies here too, and the retrofit is exactly when a second repo's
copy becomes visible enough to judge. Note this is a different question from the tooling retrofit
and does not block it: `repo-tasks` is quality-tooling-and-dev-loop only today, and widening its
remit is a decision on its own.]

## Recommended direction

One repo at a time, least-diverged first, each in its own session — this is substantial work in
another repo, not a cross-repo drive-by. Per repo: adopt `repo-tasks` (`tasks.py` collapses to
`from repo_tasks import ns`), move to `src/` layout, run `inv configure` so `configs.pull` and
`ensure-deps` establish the canonical config and dependency group, then `copier update` against
`scaffoldapy` for the structural remainder. `repo-tasks`' own
[`contributing/consumer-sweep.md`](https://github.com/TheodoreAD/repo-tasks/blob/main/contributing/consumer-sweep.md)
owns the procedure for verifying a consumer afterwards and the pitfalls around claiming one is
verified — read it before starting rather than re-deriving the checks.

Expect the `src/` move to be the real work and the tooling swap to be the easy half. Verify each
repo with its own `inv quality.precommit` from its own venv, and watch for the shadowing trap the
retired plan hit: a same-named package already editable-installed from another repo silently tests
the wrong copy.
