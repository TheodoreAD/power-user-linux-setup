---
status: landed
updated: 2026-09-10
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

## Answered by the run (2026-09-10)

**The pin does want its own commit, and the sweep wanted three rather than two.** It landed as
`14d7796` (pin plus the generated `docs/tasks.md`), `846b6c7` (the three pulled configs) and
`96df342` (the `hadolint-py` exclusion and its lock effect). The lock carried two unrelated concerns
in one file, so the split needed the scratchpad procedure from the global rules — copy the finished
file out, reduce it to one concern, gate, commit, restore — and each of the three states was gated
on its own before its commit. That is what confirms a split actually decomposes rather than merely
looking tidy.

**`docs/tasks.md` is not separable from the pin, which the plan did not anticipate.** It is
generated from the live namespace, and v0.3.0 reworded a `configs.diff` docstring, so `test_catalog`
fails on the pin alone. Any future consumer sweep here bumps the pin and regenerates in one commit.

**The `hadolint-py` reading was right.** `configs.ensure-deps` reported it `already present` and
left the bare entry alone, exactly as the additive behaviour predicts; the constraint had to be
typed by hand and `configs.diff`'s next-steps output is what says so. The reason behind the manifest
entry, worth carrying because it is invisible from this side: 2.15.1.2's macOS universal2 wheel is a
corrupt zip as published, and Linux is unaffected — so nothing in this repo's own gate could ever
have caught it, and the constraint protects whoever resolves this lock on a Mac.

**The `configs.require_tool` reading was also right, and this run did not close it.** None of the
four items was a gate binary, so `repo-tasks`' open item about that preflight never firing from a
consumer's CI stands untouched. Reported back rather than assumed.

**The falsified link-check prediction held on the inside too.** The plan measured it from outside
with the global v0.3.0 tool; `inv docs.link-check` run here after the bump, with the strict version
actually installed, reports nothing.

## Verification

- `inv configs.diff` — `up to date`, so all four items are closed.
- `inv quality.precommit` — PASS, 16 steps, run four times: once per commit state and once on the
  finished tree.
- `inv docs.link-check` — no output, exit 0.
- `uv.lock` resolves `repo-tasks` at `0.3.0` (`46d28604`) and `hadolint-py` at `2.14.0.1`.

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

## Migrated to

- [`contributing/repo-family-architecture.md`](../contributing/repo-family-architecture.md), "Taking
  a `repo-tasks` bump here" — the one finding with no other home: the generated task index is not
  separable from the pin, and why this repo is the only consumer exposed to it.
- The store, filed for `repo-tasks` as `2026-09-10-power-user-linux-setup-swept-to-v0-3-0.md` — the
  result reported back to `plans/2026-08-25-consumer-transitions.md`, which was waiting on this
  repo, plus the two sweep-doc questions that are that repo's to answer.
- The commits themselves, `14d7796`/`846b6c7`/`96df342`, which carry the reasoning for each of the
  three concerns the lock's diff mixed together.

Deliberately not migrated:

- **The sweep sequence and the `configs.diff`-reads-the-pinned-tool pitfall.** Both are owned and
  kept current by `repo-tasks`' `contributing/consumer-sweep.md`; a second copy here would be a
  diverging authority, which the retirement rule's sibling-repo clause exists to prevent.
- **The four-item drift table.** A snapshot of a moving target — that was the plan's own finding
  about itself, and `inv configs.diff` regenerates the real answer in one command.
- **The staged-`ci.yml` pitfall.** It described one tree at one moment in 2026-09-08 and had already
  cleared by the time the sweep ran.
- **The three-way commit split and its scratchpad procedure.** Already the global rule in
  `~/.agents/AGENTS.md` under "Committing multi-part work"; this run was an instance, not a source.
