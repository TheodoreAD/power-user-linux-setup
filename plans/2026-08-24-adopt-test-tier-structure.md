---
status: landed
updated: 2026-08-24
depends_on: [repo-tasks]
---

[DECISION: landed 2026-08-24 as the third option — `tests/unit/` with no integration tier. The
second open question was measured, not guessed: all 282 tests run in 0.33s and every `subprocess`/
`c.run`/network hit in the suite is a monkeypatched collaborator, so nothing qualifies for a tier
whose contract is "needs a real external service". The 16 files moved (`git mv`, history intact),
`inv configs.pull` then brought in the shared `pytest.ini` (`testpaths = tests/unit`, the `smoke`
marker) with the directory already in place, and `tasks/__init__.py` now publishes `repo_tasks`'
`testing` module as `inv test.*`. The "why the tier is empty" record lives in `tests/README.md`,
which is where the next reader looks; CI stays on `inv quality.check` alone — an
`inv test.integration` step would only no-op here.]

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

"The suite keeps passing" is the benign case, not the general one. In `scaffoldapy` the same pull,
made before the split existed, broke collection outright — exit 2, not a warning: that repo has a
_second_ `tests/` tree under `template/`, and the fallback search reached
`template/tests/conftest.py`, which then shadowed the real `tests/conftest.py`
(`ImportError: cannot import name 'BASE_ANSWERS' from 'conftest'`). One `tests/` tree at the root is
what makes the fallback survivable here; that is a property of this repo, not of the fallback.]

[PITFALL: pulling the config _before_ adopting the structure it names is the ordering that causes
the above. Adopt `tests/unit/` first, then `inv configs.pull`, then run the gate — a config pull is
not inert. Generalized into `~/AGENTS.md` under "Regenerating a file from a canonical source".]

The concrete hazard this repo had — a 144 MB gitignored `reference/` research dump in the fallback's
path — is **gone as of 2026-08-24**: its third-party material moved to `$RESEARCH_HOME` and the
directory was removed along with its `.gitignore` entry. What remains is the general shape: any
non-test directory at the repo root joins the default run if `testpaths` ever misses.

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

## Worked precedent: `scaffoldapy`, 2026-08-24

The sibling plan landed there the same day, and answers the shape of both questions above without
settling them here — that repo's tests differ from this one's.

- **It took the full split, and the split earned itself.** One test function (ten parametrizations)
  was 49.8s of a 55.9s suite and the only thing needing network, `uv`, and the global `repo-tasks`
  install; everything else totalled ~6s. The deciding argument was not conformity but that leaving a
  network-dependent test inside a tier whose contract reads "no network, nothing outside `tmp_path`"
  makes the family convention mean something different per repo. Read the same way here, the second
  question below is the whole decision: if `test_deploy.py`/`test_docker.py`/the allowlist tests
  don't actually shell out, the third option (a `tests/unit/` that merely matches the shared config)
  is the honest one, and the tier stays empty on purpose.
- **The e2e stayed in CI.** `ci.yml` gained an `inv test.integration` step rather than following
  `repo-tasks`' opt-in precedent, because that tier's prerequisites there are all things CI already
  provides — unlike `repo-tasks`' Docker daemon. The step no-ops cleanly with no integration tier,
  so it is safe in any repo.

[PITFALL: with a tier-local `tests/integration/conftest.py` present, `from conftest import X`
resolves to a _different file per tier_ — `tests/conftest.py` from the unit tier, the tier-local one
from the integration tier, where it raises `ImportError`. Silent and direction-dependent. Shared
constants that feed `@pytest.mark.parametrize` cannot be fixtures, so they need a distinctly-named
module (`tests/support.py` there), not `conftest.py`. Only bites a repo that grows a second
conftest, so it applies here only if this repo takes the real two-tier split.]

## Recommended direction

The `reference/` hazard is already resolved, so what is left is the split itself: adopt it if the
second open question turns up real integration tests; otherwise take the third option (a
`tests/unit/` that simply matches the shared config) and record why the tier stayed empty, so the
next reader does not think it was forgotten.
