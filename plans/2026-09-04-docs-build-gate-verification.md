---
status: blocked on the placement decision filed as 2026-09-04-docs-build-placement-was-superseded
updated: 2026-09-04
source_repo: github.com-personal/repo-tasks
source_session: 1f762304-ee1a-4bfb-a78f-52da747d29e3.jsonl
source_moment: 2026-09-04T23:48:52+03:00
---

# Confirm the gated docs build actually catches the anchor that broke Pages twice

## Context

`repo-tasks` landed the fix this repo asked for. `quality.check` now runs `zensical build --strict`
as `docs.build`, so a dangling anchor fails the run people already watch instead of only the Pages
deploy. Filed here because the last step belongs in this repo and cannot be done from `repo-tasks`.

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
- It is in `quality.check`, so `quality.precommit` reaches it through `check`, and CI reaches it
  too.

## Open questions

~~[NEEDS CLARIFICATION: does this repo's CI actually have zensical when it runs
`inv quality.check`?]~~ **Answered — it does, and the one-line change this anticipated was already
made.** `1df8fed` (2026-09-04, before this plan was filed) put the pin in a `docs` dependency group
_and_ added `[tool.uv] default-groups = ["dev", "docs"]`, precisely because an opt-in group is one
`inv dev-env.setup` — and therefore `ci-bootstrap.sh`, which is only `uv run inv dev-env.setup` —
never installs. So the preflight cannot fire here, and CI has zensical whichever chain reaches it.

[NEEDS CLARIFICATION: is the `zensical==0.0.44` pin still the right one to gate on? The pin exists
because a local 0.0.57 and CI's 0.0.44 disagreed about a `[certs]` table cell and shipped a red
deploy on 2026-09-02. Now that the same build runs in the gate, local and CI run the same command —
so the pin is doing more work than before and is worth a deliberate look rather than inheriting.]

## The placement it verifies is not the placement that was decided

**Read this before step 1 — it may make the whole verification moot.** This plan, and the
`repo-tasks` change it verifies, put `docs.build` in **`quality.check`**. That was the original
decision here, and it was **superseded in this repo on 2026-09-04** —
`plans/2026-09-04-precommit-does-not-build-the-docs.md`, "Revision" — at the user's own direction:
_"in theory, docs.build should be in apply, check shouldn't mutate"_, then _"i agree with docs build
in precommit"_.

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

[NEEDS CLARIFICATION: which placement stands? Filed to `repo-tasks` as
`2026-09-04-docs-build-placement-was-superseded.md`. **Until it is answered, this repo is
deliberately pinned at `cef6894`, which predates the change** — so `inv quality.check` here does not
build docs and does not mutate. Step 1 below would take the newer pin and adopt the placement in the
same move, which is why it must not run first.]

## Recommended direction

1. **Update the `repo_tasks` this repo resolves** — `configs.pull` and whatever moves the installed
   package — then check `inv -l` shows the gate step and `inv quality.check` runs it. **Blocked on
   the placement question above**; taking the pin is what adopts `check`.
2. **Reproduce the original failure and watch it fail.** Re-break the anchor the way `e7b481e` did —
   rename a heading and leave an inbound link pointing at the old fragment — and confirm
   `inv quality.check` now exits non-zero naming the anchor, where it previously passed. That is the
   check that closes this: a green run proves nothing, exactly as with the Node 20 annotations.
3. Then restore the anchor and confirm the gate goes green again, so the failure is attributable to
   the anchor rather than to anything else the update moved.
4. Answer the CI question above before pushing, since this repo pushes straight to `master`.
