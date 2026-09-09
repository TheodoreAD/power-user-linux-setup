---
status: idea
updated: 2026-09-08
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

## Open questions

[NEEDS CLARIFICATION: where does this belong once confirmed — a sentence on `setup.toml`'s `zshenv`
field comment, `docs/configuration.md`, or the `~/AGENTS.md` fragment that already carries the
`SSH_AUTH_SOCK` rule? The last is where the wrong intuition actually comes from, so stating both
halves in one place has an argument for it; against, that fragment is about ssh rather than about
this repo's deployment mechanism.]

[NEEDS CLARIFICATION: does the same hold for `zshrc` and `zprofile`? It should not — those are read
by interactive and login shells respectively, and an agent's Bash call is neither — which would make
`zshenv` the only one of the three with this property. Worth confirming rather than assuming, since
a snippet declared on the wrong field would then silently never reach a running session at all, and
the symptom would be identical to the mistaken prediction above.]

## Recommended direction

Confirm the `zshrc`/`zprofile` half, then write the whole rule wherever the previous answer lands —
one sentence saying which of the three fields reach a running agent session and which need a new
one.
