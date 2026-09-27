---
status: planned
updated: 2026-09-27
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

## Open questions

[NEEDS CLARIFICATION: take all eight lags in this sweep, or only `invoke-stubs`? The others are
patch or minor bumps of gate tools, and each may move the gate's findings.]

## Recommended direction

Run the sweep as documented, with `inv deps.check-currency` after the lock step, then
`inv deps.lock --package invoke-stubs` at minimum. Declare `plans*` under `[pyright] unchecked` once
the file confirms it is a probe. Stamp last with `inv repo-tasks.stamp`.
