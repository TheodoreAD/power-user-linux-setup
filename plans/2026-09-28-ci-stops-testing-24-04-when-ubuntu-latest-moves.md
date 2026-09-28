---
status: in-progress
updated: 2026-09-28
source_repo: github.com-personal/invoke-stubs
source_session: 76d98521-8e7c-4524-bb4f-4caeb36e8cb0.jsonl
source_moment: 2026-09-28
source_plan:
---

# `ubuntu-latest` becomes 26.04 from 2026-10-19, and this repo targets 24.04

**Deadline: the rollout starts 2026-10-19 and completes by 2026-11-19.** After that, every job here
on `ubuntu-latest` runs on a different OS from the one this repo says it targets.

## Context

GitHub's announcement is actions/runner-images#14748 (2026-09-17). `ubuntu-latest` moves from
24.04.5 to 26.04.1, with a new kernel, systemd 255 → 259, and different system package versions.
Their mitigation is to pin `ubuntu-24.04`, or to use `ubuntu-26.04` to test ahead. Every job run now
annotates the notice. It was first noticed on invoke-stubs' first CI run.

This repo is the one in the family where that matters. Everywhere else, uv manages Python and the OS
is incidental. Here the OS is the product:

- `ci.yml`'s `netdoctor-python-floor` comment says "this repo targets 24.04". The job pins Python
  3.12 with `actions/setup-python`, so it keeps passing on 26.04. But its reason, 24.04's system
  `python3`, stops being what the runner has.
- `runtime-guardrail` dry-runs `apt.install-repos apt.install-base apt.install-debs` on
  `ubuntu-latest`. On 26.04 that plans against a different codename, different package names, and
  third-party apt repos that may not publish for the new release yet.
- `install-smoke.yml`, `quality.yml`, `devcontainer.yml` and `publish_on_push.yml` also run on
  `ubuntu-latest`. The devcontainer's own base image is set separately, which is worth checking in
  the same pass.

## Open questions

[DECISION: **keep targeting 24.04 for now, and pin.** The plan named the user's own machine as the
tiebreaker, and it runs 24.04 (`/etc/os-release`, 2026-09-28). `5e4be9d` pinned `runtime-guardrail`,
`netdoctor-python-floor`, `install-smoke` and the devcontainer smoke test to `ubuntu-24.04`, and
left `quality`, `docs` and the Pages deploy floating. 26.04 support is the measurement below, not a
question for now.]

[UNVERIFIED: **the pinned jobs have not run on the pinned image yet.** The next push runs
`runtime-guardrail`, `netdoctor-python-floor` and `install-smoke` through `ci.yml`. The devcontainer
job is `workflow_dispatch`-only.]

Step 4 below is answered: `.devcontainer/devcontainer.json` uses
`mcr.microsoft.com/devcontainers/base:ubuntu-24.04`, and `docker/Dockerfile` is `FROM ubuntu:24.04`.
Both are pinned, and neither follows "latest". `config/actrc` already maps `ubuntu-24.04` for `act`.

## Measuring the risk of 26.04 over 24.04

The move-or-stay question needs a measured cost of 26.04, and most of it can be measured locally in
a container before any workflow changes.

1. **Every apt source in `setup.toml` against 26.04's codename.** For each third-party repo that
   `apt.install-repos` adds, check whether it publishes for 26.04: does `dists/<codename>/Release`
   exist? A repo that does not publish yet is the likeliest hard failure, and nothing on this side
   can fix it.
2. **The install path in `ubuntu:26.04`.** In a throwaway `docker run ubuntu:26.04` container, run
   `install.sh --bootstrap-only`, then the same `PULSE_DRY_RUN=1` apt tasks `runtime-guardrail`
   runs, then `apt.install-base` for real. The dry run cannot see a package that no longer resolves,
   but the real run can. Record per package: installs, renamed, removed, or from a repo that has not
   published yet. Run the same thing in `ubuntu:24.04` as the control, so a failure is known to come
   from the release and not from the method.
3. **The system Python.** Record `python3 --version` on 26.04 against netdoctor's floor. The
   `netdoctor-python-floor` job's premise is 24.04's 3.12.
4. **The devcontainer base image.** Check what OS release it is built on, since that is set
   separately from `runs-on`, and whether its tag follows "latest".
5. **Then CI, once.** Add `ubuntu-26.04` as a second leg on `runtime-guardrail`, `install-smoke` and
   the devcontainer build, with `fail-fast: false`, for one `workflow_dispatch` run. Record pass or
   fail per job on each image.
6. **What the result means**, stated in the plan before running it:
   - Everything installs on 26.04: moving costs little, and the question becomes only when your own
     machine moves.
   - A few packages were renamed: the cost is a list of edits to `setup.toml`, sized by the table.
   - A third-party repo does not publish for 26.04: stay on 24.04 and pin the OS jobs until it does.
     Nothing else unblocks it.

## Recommended direction

The pin is done (`5e4be9d`), ahead of 2026-10-19, and it keeps CI testing the target during the
rollout. What is left is the measurement: steps 1 to 3 locally, then step 5. It decides whether a
second `ubuntu-26.04` leg follows, and when the pin can come off. Nothing here is urgent any more.
Revisit when the owner's machine is about to move to 26.04. The family-wide choice between floating
and pinning for the uv-based repos is filed for repo-tasks as
`2026-09-28-ubuntu-latest-moves-to-26-04-from-2026-10-19.md`.
