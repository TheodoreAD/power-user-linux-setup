---
status: landed
updated: 2026-09-28
source_repo: github.com-personal/repo-tasks
source_session: bcf810d6-38c7-48d3-adfe-2ff30399d4c9.jsonl
source_moment: 2026-09-27
source_plan:
---

# Sweep to repo-tasks v0.5.0

## Context

`repo-tasks` `v0.5.0` was released 2026-09-27 and this machine's global tool is on it. Run the sweep
as `repo-tasks`' `contributing/consumer-sweep.md`, "The sweep", describes it; this repo pins
`repo-tasks` in its own `uv.lock`, so `inv deps.lock --package repo-tasks` and a sync come first.

What `v0.5.0` adds that this sweep uses:

- `inv deps.check-currency`, run after `inv deps.lock`: which `repo-tasks-quality` entries the lock
  holds behind their latest release. A plain lock keeps old pins, so take each with
  `inv deps.lock --package <name>`.
- `inv configs.check-include`: tracked Python no pyright `include` entry covers. Fixed by
  `repo-tasks.toml`'s `[pyright] extra-include = [...]` (then `inv configs.pull`), or
  `[pyright] unchecked = [...]` for a tree left out on purpose.
- Also new, not needed for the sweep: `inv dist.check-isolated`, the pin-comment check in
  `inv ci.check-actions`, `inv repo-tasks.status --latest`, `docker.logout`/`helm.logout`,
  `venv.sync --extra/--group`.

## Evidence

Measured 2026-09-27 from `repo-tasks`' session, read-only in this tree (`git status` clean after),
with the installed `v0.5.0` tool.

**`inv deps.check-currency`: 8 of 14 manifest entries behind**, including the one that motivated the
task: **`invoke-stubs` 0.1.0, locked at `ad052ca`, while its default branch is at `f70ff01`
(0.3.0)**. It had sat there a month while `configs.diff` called this repo up to date. The other
seven are ordinary lags: `basedpyright` 1.39.10 (latest 1.40.1), `ruff` 0.16.2 (0.16.9), `shfmt-py`
4.0.0 (4.2.0), `dprint-py` 0.56.1.0 (0.57.4.0), `actionlint-py` 1.7.12.24 (1.7.12.25), `zizmor`
1.29.0 (1.30.1), `hadolint-py` 2.14.0.1 (2.15.1.2).

**`inv configs.check-include`: `plans/` holds 1 tracked `.py` file, never checked.** The check's
next step suggests `extra-include`, but a plan's probe script is evidence rather than product code,
so the likely right answer is `[pyright] unchecked = ["plans*"]`, as `repo-tasks` declares for its
own `plans/`. Confirm by reading the file.

## Decisions

[DECISION: take all eight lags in this sweep, not only `invoke-stubs`. Settled 2026-09-28 with the
user. Leaving the seven gate-tool bumps behind would schedule the same lag for the next sweep; any
new gate findings they surface are fixed here, each as its own commit.]

[DECISION: `plans/` goes under `[pyright] unchecked`, not `extra-include`. The one tracked file is
`plans/2026-09-05-web-tool-permissions-and-what-auto-actually-buys/sandbox_probe.py`, a committed
attachment — evidence for a plan, not product code — matching how `repo-tasks` declares its own
`plans/`.]

## Recommended direction

Run the sweep as documented, with `inv deps.check-currency` after the lock step, then
`inv deps.lock --package <name>` for each of the eight. Declare `plans*` under
`[pyright] unchecked`. Stamp last with `inv repo-tasks.stamp` (a no-op here, since this repo pins
through its own lock).

## What the sweep found

Done in `4190053`, 2026-09-28, as one commit: the bump, the pulled configs, the regenerated
`docs/tasks.md` and the zizmor suppressions each fail the gate without the others.

- **Seven of the eight lags moved**; `invoke-stubs` 0.1.0 → 0.3.0 among them.

[PITFALL: `hadolint-py` cannot move and `check-currency` will keep calling it behind. The manifest's
own `!=2.15.1.2` excludes the only newer release, and `check-currency` compares against the latest
release rather than the latest allowed one. Filed for `repo-tasks` as
`2026-09-28-check-currency-ignores-the-manifest-constraint.md`.]

[PITFALL: zizmor 1.30's new `self-repository` audit flags every `uses: ./...` reusable-workflow call
and proposes `uses: $/...`, which actionlint and act both reject (checked against both projects'
main branches). Declined inline on the four calls in `ci.yml` and `devcontainer.yml`, reasoning
beside the first. The family-wide fix belongs in the shipped `zizmor.yml`; filed for `repo-tasks` as
`2026-09-28-zizmor-self-repository-audit-conflicts-with-actionlint-and-act.md`.]

- **The catalog test went red on the bump**, as `repo-tasks`' sweep doc predicts: v0.5.0 changes the
  task surface. `inv catalog.render-tasks` regenerated it inside the same commit.
- **`repo-tasks.toml`'s trunk setting is live now.** The note saying it was inert at the old pin was
  dropped in the same commit.

[DEFERRED: `invoke-stubs`' default branch moved from `0c6a70b` to `504c36a` while this sweep ran,
most likely a parallel session pushing. Not chased: locking a branch someone is writing takes
unreleased work. The next sweep's `check-currency` picks it up.]

## Verification

- `inv quality.precommit`: PASS, 16 steps, 784 tests.
- `inv configs.check-include`: `plans` reported unchecked by declaration, everything else covered.
- The original repro, `inv deps.check-currency`, re-run in this repo after the sweep: 2 of 14
  behind, down from 8. The two are `hadolint-py` (the false positive above) and `invoke-stubs` (the
  branch that moved mid-sweep).
