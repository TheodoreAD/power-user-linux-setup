---
status: idea
updated: 2026-08-24
depends_on: [repo-tasks]
---

# Adopt `repo-tasks`' unit/integration test structure

## Context

`repo-tasks` landed a two-tier test layout on 2026-08-24 and ships the config half of it to every
consumer: `tests/unit/` and `tests/integration/`, `pytest.ini`'s `testpaths = tests/unit`, a
registered `smoke` marker, and a `test` namespace (`inv test.unit` / `test.integration` /
`test.smoke` / `test.regression` / `test.all`) replacing `quality.test`. Only the unit tier is in
`quality.check`/`precommit`. Rationale and the measurements behind it:
`repo-tasks/contributing/test-tiers.md`.

This repo has 17 flat `tests/test_*.py` files, no `conftest.py`, and `testpaths = tests`.

**There is a deadline of sorts.** The next `inv configs.pull` here overwrites `pytest.ini` with the
shipped one, whose `testpaths` names `tests/unit` — a directory this repo does not have.

[PITFALL: that is not an error. pytest warns
(`No files were found in testpaths ... Searching recursively from the current directory instead`)
and falls back to searching from the working directory, so the suite keeps passing. But the fallback
search is _broader_ than `tests/`, and pytest does not respect `.gitignore` — so it walks
`reference/`, this repo's 144 MB gitignored research dump. It contains no test-looking files today
(checked 2026-08-24), so nothing breaks yet; the day a vendored clone under it carries tests, they
join this repo's default `pytest` run. Verified behaviour, not speculation.]

## Open questions

[NEEDS CLARIFICATION: adopt the split, or opt out of the shared `testpaths`? This repo has no
integration tier and no obvious need for one — its tests are already fast and hermetic. Adopting
means moving 17 files into `tests/unit/` for a split whose second half stays empty. Opting out means
a per-repo `pytest.ini` divergence, which `repo-tasks` has just spent effort eliminating
(`repo-tasks/plans/2026-08-23-configs-round-trip-divergence.md`). A third option: adopt the
directory but not the tier — `tests/unit/` with nothing beside it, purely so the shared config
resolves.]

[NEEDS CLARIFICATION: if the split is adopted, does anything here actually belong in an integration
tier? Candidates worth checking: the allowlist tests (do they shell out?), `test_deploy.py`,
`test_docker.py`, `test_devcontainer.py`. If several do, the split earns itself rather than being
adopted for conformity.]

[NEEDS CLARIFICATION: `reference/` is worth resolving independently of the testpaths question. It is
superseded by the shared research library (`contributing/research-library.md`, `$RESEARCH_HOME`) and
now holds only `allowlists`. If it is dead, deleting it removes this hazard and 144 MB; if it is
live, it wants a `norecursedirs` entry or a move — but an exclude cuts against the rule of thumb
that excludes belong in `.gitignore`, which pytest ignores anyway.]

## Recommended direction

Decide the `reference/` question first — it is cheap, independent, and removes the only concrete
hazard. Then adopt the directory split if the second open question turns up real integration tests;
otherwise take the third option (a `tests/unit/` that simply matches the shared config) and record
why the tier stayed empty, so the next reader does not think it was forgotten.
