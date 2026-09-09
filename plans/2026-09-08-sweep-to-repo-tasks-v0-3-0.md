---
status: idea
updated: 2026-09-09
source_repo: github.com-personal/repo-tasks
source_session: e0a0f092-e55e-4429-95e5-1882a6b773be.jsonl
source_moment: 2026-09-08T00:00:00Z
source_plan: plans/2026-08-25-consumer-transitions.md
---

# Sweep this repo onto repo-tasks v0.3.0 — the pin is three releases back

## Context

This repo was swept 2026-09-05 (`9d57d464` -> `7bb880b0`, recorded in `repo-tasks`'
`plans/2026-08-25-consumer-transitions.md`) and **is already behind again on four items**, three
days later. That is the finding as much as the list is: the sweep is a snapshot of a moving target.

Filed from `repo-tasks` rather than performed, because writing into another repo's working tree is
out — parallel sessions share these checkouts.

**The drift was measured, not listed.** Run 2026-09-08 read-only from outside this repo, using the
installed `repo-tasks v0.3.0` tool's own `configs.diff` and `link_check` against this tree. Nothing
here was written, pulled or staged.

[PITFALL: **this tree had a staged, uncommitted edit to `.github/workflows/ci.yml` when the
measurement ran** (`git status --porcelain` reported `M` — staged, not merely modified). It was left
strictly alone and is not part of this plan. It may belong to another live session; check whose it
is before staging anything, and stage this sweep's paths individually rather than with
`git add -A`.]

## Evidence

Session `e0a0f092-e55e-4429-95e5-1882a6b773be.jsonl` under
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-repo-tasks/`, 2026-09-08. The
distinctive phrase to search that transcript for is "What both consumers are actually behind on".

The repro is one command from inside this repo — but see the pitfall below about **which**
`repo-tasks` answers it here:

```shell
inv configs.diff
```

## This repo lags differently from the other consumer

`scaffoldapy` takes `repo-tasks` as the global uv tool, so its task code is always current and only
its pulled config files drift. **This repo pins `repo-tasks` in its own `uv.lock`** —
`version = "0.2.0"`, `source = { git = "…#7bb880b0658cbd1c4670f3ae37a14cacd841cbec" }` as of
2026-09-08 — so both halves lag, and the task code half is the larger one: `v0.3.0` added the
`runner`, `interactive` and `nextsteps` modules, the link-check anchor resolution, and the
two-version `repo-tasks.status`.

[PITFALL: **`inv configs.diff` run here reads the _pinned_ `repo_tasks`, not the global tool**, so
it compares against the shipped configs as they stood at `7bb880b0`. That is why the pin bump
belongs **above** `configs.diff` in the sequence for a lock-pinning consumer — a correction this
repo's own 2026-09-05 sweep already made to `repo-tasks`' `contributing/consumer-sweep.md`, because
running `diff` first reports drift against the old shipped configs and a `pull` then writes them,
giving an identical report before and after the bump. The measurement below deliberately bypassed
that by running the **global v0.3.0** tool against this tree from outside it.]

### What this repo is behind on

| item                                                 | landed in `repo-tasks`   |
| ---------------------------------------------------- | ------------------------ |
| `ruff.toml` — `sys.path` / `site.addsitedir` bans    | `1c91c2e`                |
| `dprint.json` — sha256 checksums on all five plugins | 2026-09-06               |
| `pytest.ini` — the starlette `anyio` ignore          | `487c9c8`                |
| dev group — `hadolint-py` missing `!=2.15.1.2`       | manifest, date not taken |

`scaffoldapy` reports **identical** config drift, so none of this is specific to this repo. What is
specific is the pin: that repo has the task code already and this one does not.

### The link-check question, answered in advance

`7fc0b23` made `docs.link-check` resolve a link's fragment against the target's real headings. It is
a gate step and strictly stricter, so the `repo-tasks` checklist flagged it as able to turn a green
consumer **red on links nothing has ever checked** — and unlike `scaffoldapy`, this repo genuinely
does not have it yet, so the risk was live here.

**Measured: it is empty.** Running the v0.3.0 `link_check` against this tree reports no broken
links, so the bump will not turn the gate red on this account. The sequencing the checklist asked
for is withdrawn.

## Open questions

[NEEDS CLARIFICATION: does the pin bump want to be its own commit ahead of the config pull? The
2026-09-05 sweep ran `inv deps.lock --package repo-tasks` first and the rest after, which is the
ordering `contributing/consumer-sweep.md` now documents — but it landed as one sweep. Splitting it
would make "the pin moved" and "the configs followed" separately revertible, which matters more now
that the task-code half is three releases wide rather than a few commits.]

[NEEDS CLARIFICATION: the `hadolint-py` constraint is a dev-group edit and `configs.ensure-deps` is
additive — it will not rewrite an entry already present, so this is a hand edit per `configs.diff`'s
own next-steps output. Confirm that is still true rather than assuming.]

[NEEDS CLARIFICATION: `repo-tasks`' own `plans/2026-08-25-consumer-transitions.md` still carries an
`[UNVERIFIED:]` that `configs.require_tool`'s preflight has never fired from a consumer's own CI.
None of the four items above is a gate binary, so this sweep cannot answer it either — worth
confirming that reading rather than hoping this run closes it.]

## Recommended direction

Pin first, then the configs — the ordering this repo's own last sweep established:

```shell
inv deps.lock --package repo-tasks   # move the pin off 7bb880b0
uv sync
inv configs.diff                     # now compares against v0.3.0's shipped copies
inv configs.pull
# then edit dependency-groups.dev by hand: "hadolint-py" -> "hadolint-py!=2.15.1.2"
inv configs.ensure-deps
inv deps.lock                        # review the diff
uv sync
inv quality.precommit
```

`inv venv.sync` has no meaning here — this repo publishes no `venv` collection, so plain `uv sync`
is the step. That correction is also from the 2026-09-05 sweep.

**Do not start from `repo-tasks`' sweep checklist.** Measured 2026-09-08, it named one of these four
items; two more were found by reading source that morning and two only by running `configs.diff`
against the installed tool. The command is the list.
