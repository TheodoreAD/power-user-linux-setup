---
status: landed
updated: 2026-09-05
source_repo: github.com-personal/repo-tasks
source_session: 1f762304-ee1a-4bfb-a78f-52da747d29e3.jsonl
source_moment: 2026-09-04T23:48:52+03:00
---

# Confirm the gated docs build actually catches the anchor that broke Pages twice

## Context

`repo-tasks` landed the fix this repo asked for. Filed here because the last step belongs in this
repo and cannot be done from `repo-tasks`.

[PITFALL: **as filed, this paragraph said `quality.check` runs the build, and that is no longer
true** — `7a41c1e` moved it to `precommit` a few hours later, for the reason in "The placement it
verifies" below. The sentence is corrected rather than deleted, because a filed plan is a snapshot
of what its author knew and this one was overtaken twice while it sat in the queue.]

The fix is verified **in `repo-tasks`**: five unit tests, and `inv docs.build` no-opping on a repo
with no `mkdocs.yml`. What is not verified is the case that produced the plan — a real dangling
anchor in a real 41-page site — because `repo-tasks` has no docs site to reproduce it with. The
`plan-docs` convention is explicit that a cross-repo fix verified only where it was written has not
been tested against the case that produced it, which is why this exists rather than the plan simply
being retired there.

## Evidence

The original repro, from this repo's own `plans/2026-09-04-precommit-does-not-build-the-docs.md` and
the plan filed to `repo-tasks` from it: a heading rename in `docs/claude-code.md` (`e7b481e`)
changed its anchor while `docs/index.md:63` kept linking to the old one. `CI` passed green on
`2a4de19` and on `ae59318` while `Deploy docs to GitHub Pages` failed on both, so `master` moved
twice with the published site serving the last good build.

Measured then, in this repo: `inv docs.build` 1.54 s and 1.59 s wall on 41 pages;
`inv quality.precommit` 6.76 s. `docs.link_check` exits 0 on that input, `zensical build --strict`
exits 1 with `anchor does not exist … Aborted because --strict flag is
set`.

What landed in `repo-tasks`, 2026-09-04, and matters for how this is checked here:

- `docs.build` no-ops when there is no `mkdocs.yml`. This repo has one, so it does **not** no-op
  here — this is the one consumer where the step actually runs.
- The zensical preflight is **not** `configs.require_tool`. It names `uv sync --group docs`, because
  zensical is in this repo's own `docs` group rather than in the `repo-tasks-quality` manifest. This
  repo already has that group (`docs = ["zensical==0.0.44"]`), so the preflight should never fire;
  if it does, that is the finding.
- ~~It is in `quality.check`, so `quality.precommit` reaches it through `check`.~~ Superseded: it is
  in `precommit` only, and CI reaches the docs build through `ci.yml`'s own `docs` job instead.

## Open questions

~~[NEEDS CLARIFICATION: does this repo's CI actually have zensical when it runs
`inv quality.check`?]~~ **Answered — it does, and the one-line change this anticipated was already
made.** `1df8fed` (2026-09-04, before this plan was filed) put the pin in a `docs` dependency group
_and_ added `[tool.uv] default-groups = ["dev", "docs"]`, precisely because an opt-in group is one
`inv dev-env.setup` — and therefore `ci-bootstrap.sh`, which is only `uv run inv dev-env.setup` —
never installs. So the preflight cannot fire here, and CI has zensical whichever chain reaches it.

~~[NEEDS CLARIFICATION: is the `zensical==0.0.44` pin still the right one to gate on?]~~ **Answered:
yes, and the question conflates two things.** What the pin has to guarantee is that the gate, CI and
the deploy build with the _same_ version — the 2026-09-02 red deploy happened because a local 0.0.57
and CI's 0.0.44 disagreed about whether a `[certs]` table cell was a link reference. That property
comes from having _a_ single pin, resolved from `uv.lock` by every consumer of it, and it holds
today: `inv docs.build`, `ci.yml`'s `docs` job and `publish_on_push.yml` all read the same one.

**Which** version it is, is a separate and deliberate bump, not something to inherit. Latest is
0.0.59 against a pinned 0.0.44 (checked 2026-09-04), and two things argue against drifting to it
casually: zensical is early alpha and its versions demonstrably disagree about what valid markdown
is — which is the whole reason this repo has a pin — and 0.0.44 is ~30% slower than 0.0.57, so a
bump is also a gate-latency change worth measuring rather than absorbing.

[DECISION: keep `0.0.44` and treat a bump as its own task. It is now much cheaper and safer than it
was: the gate builds the docs, so a version that disagrees about this repo's markdown fails locally
before anything is pushed, where in September it could only fail the deploy. Re-run
`contributing/zensical.md`'s "Checklist for next time" against the new version when it happens.]

## The placement it verifies was not the placement that was decided — RESOLVED

**Resolved the same night, in `precommit`'s favour; kept because it records how two sessions
diverged on a stale artefact and how that was caught.** This plan, and the `repo-tasks` change it
verifies, put `docs.build` in **`quality.check`**. That was the original decision here, and it was
**superseded in this repo on 2026-09-04** — `plans/2026-09-04-precommit-does-not-build-the-docs.md`,
"Revision" — at the user's own direction: _"in theory, docs.build should be in apply, check
shouldn't mutate"_, then _"i agree with docs build in precommit"_.

The two sessions diverged on a stale artefact, and the chain is worth stating because nothing in
either repo shows it:

1. This repo filed `2026-09-04-docs-build-in-the-quality-gate.md` for `repo-tasks`, saying `check`.
2. This repo then revised that to `precommit` and flagged, twice, that the filed copy was now stale.
3. The `repo-tasks` session implemented the filed copy faithfully and retired it (`c296ad8`).

So what shipped carries the superseded reasoning verbatim — `check`'s docstring now argues "it is in
`check` rather than in `precommit` because only `check` reaches CI", which is the exact argument the
revision answered: `check` is the read-only half by construction, and zensical offers **no** way to
build without writing (probed 2026-09-04 — no output flag, and an out-of-tree `site_dir` panics on a
Rust invariant). CI coverage was solved differently here, by giving `ci.yml` its own `docs` job on
both `push` and `pull_request`.

[PITFALL: **the CI argument is genuinely stronger for other consumers, and that is why this needs a
decision rather than a revert.** A `scaffoldapy`-generated repo with a docs site and no docs CI job
gets its only CI coverage from `check`. The counter is that a consumer adds a `docs` job the way
this repo just did, and that `check` mutating breaks its contract for _every_ consumer including the
ones with no docs at all. Both readings are defensible; what is not defensible is the two repos
holding opposite answers while each believes the question settled.]

[PITFALL: **a third answer landed in `repo-tasks` while this was being written, and it may retire
the question rather than settle it.** `7fc0b23`/`31cbf44` — committed, **not yet pushed**, in
another session's tree, so hands-off and not to be built on — give `link_check` real anchor
resolution, against the union of python-markdown's `toc` slugger and github.com's. If that holds up,
the anchor class is caught by a check that needs no zensical, writes nothing, already sits in
`check` legitimately, and **covers the files zensical never builds** — which closes this repo's own
recorded coverage bound, the three `AGENTS.md`/`contributing/` anchors that had to be verified by
hand because `--strict` only walks `docs_dir`. The docs build would then be defence in depth rather
than the only detector, and where it sits matters much less. Do not treat this as settled: it is
unpushed work in progress, and the two sluggers agreeing on the common case is exactly where a
union-of-two-sluggers check earns its keep or does not.]

~~[NEEDS CLARIFICATION: which placement stands?]~~ **Answered 2026-09-04 in `repo-tasks`, in favour
of `precommit`.** `7a41c1e` — "Move the docs build out of check, which must not mutate" — puts it in
`pre=[fix, check, docs_build]`, and `9d57d46` retired the plan this repo filed. The filed plan was
absorbed, acted on and retired inside about half an hour, which is the cross-repo mechanism working
end to end rather than a plan sitting in a queue.

## Verified 2026-09-04: it catches the failure, and `check` still writes nothing

Steps 2 and 3 below, run against the pin that carries the correction (`9d57d46`):

| what was run                                  | result                                                                |
| --------------------------------------------- | --------------------------------------------------------------------- |
| `docs/index.md:63` re-broken as `e7b481e` did | —                                                                     |
| `inv quality.check`                           | **exit 1** — `docs/index.md:63: … (no such anchor in claude-code.md)` |
| `site/` after that run                        | **absent** — the read-only property holds                             |
| anchor restored, `inv quality.precommit`      | **exit 0**, and it does leave a 3.3 MB `site/`                        |

**What catches it is not the docs build.** `link_check` gained real anchor resolution in the same
window (`7fc0b23`), resolving against the union of python-markdown's `toc` slugger and github.com's,
so the class that shipped two red deploys is caught by a check that needs no zensical and writes
nothing. The docs build in `precommit` is defence in depth behind it.

That also closes this repo's recorded coverage bound: `--strict` only walks `docs_dir`, so the three
anchors in `AGENTS.md` and `contributing/` had to be verified by hand — a link checker that reads
anchors covers those files too.

[PITFALL: the bump moved the task surface again and
`test_committed_task_index_matches_the_namespace` failed a second time, on `quality.precommit`'s own
summary line changing to "Fix, then check, then build the docs site". That test's docstring predicts
exactly this — it goes stale with no commit in this repo — and it is the reason a `repo-tasks` bump
is never a one-file change here.]

## Migrated to

Retired 2026-09-06. Every step below is done, the deletion gate is clean (no open `DEFERRED` or
`UNVERIFIED`), and `refs` found no inbound links.

- **`contributing/zensical.md`, "Renaming a heading is an anchor change"** — rewritten rather than
  extended, because what was there had gone false in three places: it claimed `--strict` is the only
  check that sees an anchor, that `docs.link-check` stops at the `#`, and that the docs build
  joining the gate was still pending. It now describes both checks, names the `docs_dir`-only
  coverage bound that makes `link_check` the one covering `AGENTS.md`/`contributing/`/`plans/`, and
  keeps the two red deploys as the evidence. Re-verified against the pinned `repo_tasks` before
  writing, not copied from this plan: `_bad_link` resolves fragments against the union of the `toc`
  and github sluggers, and `quality.precommit` is `pre=[fix, *_CHECKS, docs_build]`.
- **`contributing/zensical.md`, "Checklist for next time"** — the `[DECISION:` on keeping `0.0.44`,
  with the 2026-09-02 red deploy that a single pin exists to prevent and the reason a bump is now
  cheap to attempt but still deliberate.
- **`contributing/repo-family-architecture.md`, "Landing a change the test assigns to a sibling
  repo"** — the divergence itself, generalised. It sits under "The test that actually settles it"
  because that section answers which repo owns a change and this one answers how it gets there.

Deliberately not migrated:

- **The placement decision itself.** `repo-tasks` owns it and states it currently, in
  `quality.precommit`'s docstring together with the argument it beat. A second copy here would
  diverge, which is the specific failure this plan is about.
- **The verification table, the `## Evidence` block and the timings.** A log of one afternoon's
  runs; the property it established is now asserted by the gate on every commit.
- **The `test_committed_task_index_matches_the_namespace` pitfall.** Already in that test's own
  docstring, checked rather than assumed: "a `repo-tasks` bump changes the task surface here".
- **The stale `docs.build` docstring.** Still present on `repo-tasks` `main`, saying "In
  `quality.check`" and "`link_check` strips the fragment by design" — both false in the same package
  that ships them. Filed for that repo rather than fixed from here.

## Recommended direction

1. ~~Update the `repo_tasks` this repo resolves.~~ **Done** — `02975ab` takes `9d57d46`.
2. ~~Reproduce the original failure and watch it fail.~~ **Done**, see the table above.
3. ~~Restore the anchor and confirm the gate goes green again.~~ **Done.**
4. ~~Answer the CI question before pushing.~~ **Done** — answered in Open questions above; the
   `docs` group is a default group, so `ci-bootstrap.sh` syncs zensical.
