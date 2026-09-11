---
status: landed
updated: 2026-09-11
source_repo: github.com-personal/repo-tasks
source_session: 20d8525a-71ae-4cb3-af8a-c3f83e0bcde7.jsonl
source_moment: 2026-09-08T22:10:00Z
---

# A deployed zshenv snippet reaches the running agent session, with no restart

## Context

Filed while retiring `repo-tasks`' `plans/2026-09-05-run-reporting-as-an-opt-in-agent-mode.md`. The
finding is about this repo's `zshenv` mechanism rather than about that package, so it is filed here
rather than migrated into a doc in the repo that happened to hit it.

**Deploying a `zshenv` snippet takes effect on the running session's very next Bash call.** Each
call is a fresh non-interactive `zsh -c`, and that reads `~/.zshenv` every time — so a session does
not have to be restarted, and a session that waits for one waits for nothing.

That is the opposite of what the retiring plan's own author predicted in a written report:

> existing agent sessions keep the old environment until they're restarted

The prediction was wrong, and it was wrong in the direction that costs a session: it says to stop
and restart when the next command would already have worked.

**Why the wrong intuition is easy to reach.** It is the same shape as `SSH_AUTH_SOCK`, where the
opposite is true and is already written down in `~/AGENTS.md` — an `export` typed _in_ a Bash call
dies with that call, which is exactly why that rule says to use a per-call prefix rather than an
export. Both facts follow from the same mechanism (a fresh shell per call), and they point in
opposite directions: what the shell _sources_ every time persists, what a call _sets_ does not.

## Evidence

Observed 2026-09-05 deploying `export REPO_TASKS_RUN_REPORT=1` into the `CLAUDECODE`-guarded snippet
with `inv zsh.configure`, then reading it back with `env | rg REPO_TASKS_RUN_REPORT` in the same
session — set, with no restart. `setup.toml`'s own comment on the field already implies it by saying
the snippet reaches "all shells", but does not state the consequence, which is what left room for
the prediction.

The distinctive phrase to search the source session's transcript for is "keep the old environment
until they're restarted".

## Answered (2026-09-11)

**Where it belongs: nowhere new.** `contributing/session-environment.md` already opened with the
fact — `~/.zshenv` is read on every zsh invocation, and nothing else in the startup sequence is — so
the missing half was never the fact but its consequence for a running session. That is now a section
on the same page, next to the thing it follows from. It is deliberately **not** a new rule in
`~/.agents/AGENTS.md`: the fact is already stated where the mechanism is explained, and the miss it
prevents is cheap and recoverable — you wait for a restart you did not need — which is the tier test
that keeps a rule out of the always-loaded set.

**`zshrc` and `zprofile`: the guess was right, and the way you would check it is wrong.** Measured
with `ZDOTDIR` pointed at a scratch directory holding one marker per startup file, so nothing real
was touched:

| invocation                         | `.zshenv` | `.zshrc` | `.zprofile` |
| ---------------------------------- | --------- | -------- | ----------- |
| `zsh -c` — what the Bash tool runs | **yes**   | no       | no          |
| `zsh -l -c`                        | yes       | no       | **yes**     |
| `zsh -i -c`                        | yes       | **yes**  | no          |

[PITFALL: **checking it the obvious way gives the opposite answer.** `setopt` inside an agent's Bash
call reports `login`, which reads as proof that `~/.zprofile` is sourced every call. It is not: the
invocation is a bare `zsh -c`, and the per-session snapshot it sources ends with a literal
`setopt login` restoring the option state of the interactive shell it was captured from. Variables
that only `.zshrc` or only `.zprofile` set are visible for the same reason — the snapshot carries
their values — while an edit to either reaches nothing until a new session. A present value means
"captured once", not "read every call".]

## Recommended direction

Confirm the `zshrc`/`zprofile` half, then write the whole rule wherever the previous answer lands —
one sentence saying which of the three fields reach a running agent session and which need a new
one.

## Migrated to

- [`contributing/session-environment.md`](../contributing/session-environment.md), "A deployed
  `zshenv` snippet reaches a running agent session, with no restart" — the consequence, the
  three-file table, and the `setopt login` trap, placed next to the fact they follow from.
- [`AGENTS.md`](../AGENTS.md), "Running the test suite" — the snapshot gotcha was true and too
  broad. It now says which half is read once (`.zshrc`, where direnv's hook lives, which is why the
  original sentence was right about direnv) and which is read every call.

Deliberately not migrated:

- **A new rule in `~/.agents/AGENTS.md`.** Ruled out on the tier test rather than on space: the miss
  costs a restart you did not need, which is cheap and recoverable, and the fact is already stated
  where the mechanism is explained.
- **The wrong prediction, quoted.** It is worth one clause naming the intuition, which the
  contributing section has; the transcript citation dies with this file and the corrected statement
  is what a reader needs.
