---
status: idea
updated: 2026-09-12
source_repo: github.com-personal/repo-tasks
source_session: 5de331c8-e7f0-4bcb-a86f-c242683a382d.jsonl
source_moment: 2026-09-12T10:00:00Z
source_plan: plans/2026-09-08-status-measures-the-running-interpreter-not-the-global-tool.md
---

# Two of the tool-conflict plan's items are answered in `repo-tasks`; `bootstrap.sh` still owns its own

## Context

`plans/2026-08-23-invoke-repo-tasks-tool-conflict.md` ends with a deferred item saying
`bootstrap-repo-tasks.sh` stamps `uv tool install` without `--python` while this repo's own
`bootstrap.sh` passes `--python "${UV_PYTHON_DEFAULT}"`, "so the stamped script installs against
whatever interpreter uv happens to pick", and that it "belongs to `repo-tasks`' stamp template, not
here".

It reached that repo and was settled there the same day, **as a won't-fix with the premise
corrected**. Nothing is owed back here; this exists so the item is not re-investigated from this
side.

**The same session then did the plan's item 3** — "mirror the same check in `repo-tasks`'
`selfinstall.update`, so the human-facing update path can't recreate the split either" — so two of
the three install paths that plan names are now settled. `inv repo-tasks.update` reports a
separately-installed `invoke` uv tool and prints `uv tool uninstall invoke` as a next step; it does
not remove it and does not refuse to install, because removing another tool mutates machine state
outside that package's scope and refusing would break the one command that moves the global install.
Landed as `dbe84e4`, with five unit tests and a real-listing check.

**What is still this repo's, and is the larger half:** `bootstrap.sh` itself, where items 1 and 2
live — detect the other tool before installing either, prompt with a TTY, and decide what the
unattended default does. That plan's own `[NEEDS CLARIFICATION]` about whether the check lives here
or is composed from a `repo-tasks` task is **not** settled by the above: `update` runs after
`repo-tasks` exists, and `bootstrap.sh`'s check has to run before it does, which is exactly the
objection that question raised. The `--invoke-only` direction is also still open and still
asymmetric — removing `repo-tasks` to install bare `invoke` breaks every family repo's `tasks.py`, a
much bigger blast radius than the reverse.

## Evidence

Session `5de331c8-e7f0-4bcb-a86f-c242683a382d.jsonl` under
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-repo-tasks/`, 2026-09-12. The
distinctive phrase to search for is "Should the stamp template pin an interpreter".

Landed in `repo-tasks` as `6d30b1c` (a comment at `_INSTALL_CMD` in `selfinstall.py`) and `b9749f7`
(the full reasoning in the plan named above); the shadowing guard as `dbe84e4` and `4e407b0`. Search
that plan for "Should the stamp template pin an interpreter" and "The shadowing guard, the other
half of that item".

Three probes on uv 0.11.19, each with isolated `UV_TOOL_DIR`/`UV_TOOL_BIN_DIR` so nothing on this
machine moved:

| probe                                                | what uv reported, and chose                                      |
| ---------------------------------------------------- | ---------------------------------------------------------------- |
| the real stamped git-URL shape, `UV_PYTHON` unset    | `>=3.11` from `requires-python` metadata -> cpython 3.14.5       |
| a package declaring `>=3.9,<3.10`, `UV_PYTHON` unset | `>=3.9, <3.10` from `requires-python` metadata -> cpython 3.9.25 |
| the same package, `UV_PYTHON=3.14`                   | `3.14` from explicit request -> installed onto 3.14 regardless   |

## What this changes for this repo

**The two bootstrap scripts already agree here, and the mechanism is this repo's own `zshenv`, not
the flag.** `[packages.uv-env]` exports `UV_PYTHON="3.14"` into every shell, `uv tool install`'s
`--python` reads that env var, so a bare `uv tool install` on this machine resolves to 3.14 exactly
as the flagged one does. The deferred item's "harmless on this machine today, where uv's default and
the pinned default agree" is right about the outcome and wrong about the cause — uv's unconstrained
default never entered into it.

**Absent the env var, uv derives the request from the target's own `requires-python`** — measured
through a git URL, which is the shape the stamped script uses, so the inference survives the source
type. A bare install cannot land below a package's floor.

**The `--python` in `bootstrap.sh` is therefore belt-and-braces rather than load-bearing**, which is
a fine thing for a machine's own bootstrap to be. Nothing here needs changing. It is worth knowing
that the flag is the weaker of the two mechanisms in one specific way: an explicit request
_overrides_ `requires-python` rather than narrowing it, silently — the third probe installed a
package declaring `>=3.9,<3.10` onto 3.14 with no warning anywhere in the output. That is why
`repo-tasks` declined to put a version in a template every consumer regenerates.

## Open questions

[NEEDS CLARIFICATION: does `UV_PYTHON_DEFAULT` still earn its own name now that `[packages.uv-env]`
exports `UV_PYTHON` to the same value? `setup.toml` already carries a comment about keeping
`settings.uv_python_default` and that zshenv line in sync, and `tasks/python.py` has a regex
(`_UV_ENV_RE`) whose job is that synchronisation. Two names for one number, kept aligned by a task,
is the shape worth re-examining — not urgent, and not something `repo-tasks` has a view on.]

## Recommended direction

1. **Fold this into `2026-08-23-invoke-repo-tasks-tool-conflict.md` rather than keeping it beside
   that plan**, striking its `--python` deferred item and its item 3, and delete this file. It
   reports on that plan's own subject and has nothing of its own to carry.
2. **Then the remaining work is `bootstrap.sh`'s**, and it is the half with the open design
   questions rather than the half with the code. `repo-tasks`' side is a worked precedent for the
   message and the next-step shape, not for the policy: `update` can report and move on because the
   machine already has both tools, while `bootstrap.sh` is deciding which one to put there.
3. `repo-tasks` also left a deferred question of its own that touches this — whether a
   `repo-tasks.doctor` (or `status`) should report the shadowing case as a check rather than only as
   a side effect of updating. It declined to build it because this plan pairs the shadowing failure
   with the cwd one and says a check answering half would leave the other half undiagnosed. If
   `bootstrap.sh` ends up wanting such a check to compose, that is the argument that reopens it.
