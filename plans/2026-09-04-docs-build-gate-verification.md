---
status: idea
updated: 2026-09-04
repo: git@github.com:TheodoreAD/power-user-linux-setup.git
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

[NEEDS CLARIFICATION: does this repo's CI actually have zensical when it runs `inv quality.check`?
`.github/ci-bootstrap.sh` runs `uv run inv dev-env.setup`, and the question is whether that syncs
the `docs` group or only `dev`. If it syncs only `dev`, the new gate step will fail in CI on this
repo with the preflight message — correct behaviour, wrong moment, and the fix is a one-line change
to what CI syncs. **Check this before pushing anything**, because the failure lands on `master`.]

[NEEDS CLARIFICATION: is the `zensical==0.0.44` pin still the right one to gate on? The pin exists
because a local 0.0.57 and CI's 0.0.44 disagreed about a `[certs]` table cell and shipped a red
deploy on 2026-09-02. Now that the same build runs in the gate, local and CI run the same command —
so the pin is doing more work than before and is worth a deliberate look rather than inheriting.]

## Recommended direction

1. **Update the `repo_tasks` this repo resolves** — `configs.pull` and whatever moves the installed
   package — then check `inv -l` shows the gate step and `inv quality.check` runs it.
2. **Reproduce the original failure and watch it fail.** Re-break the anchor the way `e7b481e` did —
   rename a heading and leave an inbound link pointing at the old fragment — and confirm
   `inv quality.check` now exits non-zero naming the anchor, where it previously passed. That is the
   check that closes this: a green run proves nothing, exactly as with the Node 20 annotations.
3. Then restore the anchor and confirm the gate goes green again, so the failure is attributable to
   the anchor rather than to anything else the update moved.
4. Answer the CI question above before pushing, since this repo pushes straight to `master`.
