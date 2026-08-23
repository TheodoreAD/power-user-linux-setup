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
search is _broader_ than `tests/`, and pytest does not respect `.gitignore`. Verified behaviour, not
speculation.

The concrete hazard this repo had — a 144 MB gitignored `reference/` research dump in the fallback's
path — is **gone as of 2026-08-24**: its third-party material moved to `$RESEARCH_HOME` and the
directory was removed along with its `.gitignore` entry. What remains is the general shape: any
non-test directory at the repo root joins the default run if `testpaths` ever misses.]

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

[DECISION: `reference/` is gone. Resolved 2026-08-24 — the seven vendored clones and two docs
mirrors moved to `$RESEARCH_HOME` with `SOURCE.md` provenance, `findings.md` was preserved as
`contributing/permission-systems.md`, and `tool-rules.md`/`README.md` were dropped as superseded by
`cli-allowlist/rules/`. 144 MB and the `.gitignore` entry both removed.]

## Recommended direction

The `reference/` hazard is already resolved, so what is left is the split itself: adopt it if the
second open question turns up real integration tests; otherwise take the third option (a
`tests/unit/` that simply matches the shared config) and record why the tier stayed empty, so the
next reader does not think it was forgotten.
