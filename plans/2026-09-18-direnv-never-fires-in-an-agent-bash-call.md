---
status: planned
updated: 2026-09-18
source_repo: github.com-personal/freshful-polite-mcp
source_moment: 2026-09-18T12:05:00Z
source_session: 2888f600-fe6e-4cd8-aa7f-fcd46bc4c81d.jsonl
source_plan:
---

## Context

The always-loaded instructions file tells agents to reach for the bare command because direnv has
already put `.venv/bin` on `PATH`. direnv's hook does not fire in the shell the Bash tool runs, so
nothing re-evaluates `.envrc` as an agent moves between directories.

[PITFALL: **this file originally said the bare command "never" resolves into the venv, and that is
measurably false — the truth is worse.** Corrected 2026-09-18 by measuring a session in
`power-user-linux-setup` rather than in the filing repo. The environment is **frozen at session
start**: whatever direnv had activated when the shell snapshot was captured is carried verbatim for
the whole session and never updated. So the bare command does resolve into a venv — the **session's
origin repo's** venv. That is right while you are in that repo, which is most of a session, and
silently wrong the moment you are not. The original claim generalised from a session filed out of
`freshful-polite-mcp`, a repo with no `.envrc`, where the frozen environment was simply empty and
the failure therefore surfaced as an honest `not found`. See "Measured again, in a repo that does
have `.envrc`" below.]

The rule, under "Invoking a venv tool in the session's own project [needs direnv]":

> Check `which <tool>` before prefixing `uv run` or spelling out `.venv/bin/<tool>`: most of this
> user's repos put `.venv/bin` on `PATH` via direnv (`.envrc`), so the bare command already resolves
> into the venv and a wrapper or absolute path only adds prompt friction.

Measured 2026-09-18 in `olx-polite-mcp`, a repo that **does** have `.envrc`:

```
cd <that repo> && echo "DIRENV_DIR=${DIRENV_DIR:-unset}" && which ruff
DIRENV_DIR=unset
ruff not found
```

`DIRENV_DIR` unset is direnv saying it never ran. The same session, in a repo with no `.envrc` at
all, got `inv` from `~/.local/bin` and `ruff not found` — which is the same outcome by a different
route, and is why the difference between the two repos is invisible from inside an agent session.

[PITFALL: **the instruction is self-defeating in a way that reads as careful.** It says to run
`which` first, which is right, and then tells you what the answer will be, which is wrong. An agent
that runs the check gets `not found` and is left with no instruction at all — the rule's next
sentence is about `AGENTS.md` staleness, not about what to do. An agent that trusts the stated
premise and skips the check runs whatever `~/.local/bin` happens to hold. Both paths end somewhere
the rule did not intend, and the second one silently runs the wrong interpreter.]

[PITFALL: **the same file already contradicts this, one section away, and the contradiction points
the right way.** Under "Running a command against a different repo", it says PATH "stays the primary
project's direnv-activated `.venv/bin` (direnv hooks don't fire in non-interactive shells)". The
parenthesis is correct and is the fact this plan is about. The main clause assumes the venv _is_
activated, which the parenthesis has just denied. So the knowledge is present in the corpus and is
attached to the wrong conclusion in two places.]

## Evidence

Transcript:
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-freshful-polite-mcp/2888f600-fe6e-4cd8-aa7f-fcd46bc4c81d.jsonl`

The instance that surfaced it, 2026-09-18, distinctive phrase `direnv isn't active in this shell`:

```
inv check
-> bash: line 1: ruff: command not found     (exit 127)

which inv ruff python3
-> /home/tdumitrescu/.local/bin/inv
   ruff not found
   /home/tdumitrescu/.local/bin/python3
```

Note what `inv` resolving to `~/.local/bin/inv` means: the task runner ran, found `tasks.py`, and
began executing the repo's gate with a `ruff` that was not the repo's. It failed at 127 rather than
running the wrong linter, but only because no `ruff` existed on `PATH` at all. On a machine where a
user-wide `ruff` is installed — which is the documented setup for several tools here — the same call
succeeds against the wrong version and reports a green gate.

The user's own words on being shown it, 2026-09-18: _"the direnv thing is a problem"_.

### Measured again, in a repo that does have `.envrc`

A session in `power-user-linux-setup`, 2026-09-18, which has an `.envrc` and is `direnv allow`ed
(`direnv status`: `Found RC allowed true`). Standing in the repo itself:

```
DIRENV_DIR=-/home/…/power-user-linux-setup
VIRTUAL_ENV=/home/…/power-user-linux-setup/.venv
which -a ruff -> …/power-user-linux-setup/.venv/bin/ruff
                 …/ingesta/.venv/bin/ruff
```

So the environment **is** there, and every bare command in that session — `pytest`, `inv`, `ruff` —
had been resolving correctly all along. Then the same session, one `cd` away, in `olx-polite-mcp`,
which has its own `.envrc` and its own venv:

```
cwd=/home/…/olx-polite-mcp
DIRENV_DIR=-/home/…/power-user-linux-setup     # unchanged
VIRTUAL_ENV=/home/…/power-user-linux-setup/.venv  # unchanged
which ruff -> /home/…/power-user-linux-setup/.venv/bin/ruff
```

Three things follow, and only the first was already known:

1. **The hook does not fire per call.** `cd` into a different `.envrc` repo changes nothing.
2. **What is frozen is not nothing.** It is the origin repo's fully activated environment, so the
   bare command succeeds and returns _a_ tool — the wrong repo's, with that repo's pinned version.
   This is the silent-wrong-interpreter outcome `~/.agents/AGENTS.md`'s cross-repo section warns
   about, reproduced here as a plain measurement rather than a hypothetical.
3. **`PATH` carries a third repo's venv too** — `ingesta/.venv/bin`, second, in a session that never
   went near it. So the frozen environment is not even a clean snapshot of one repo.

[UNVERIFIED: why `ingesta` is on that `PATH` at all. The snapshot is captured once per session and
`~/.agents/AGENTS.md` already documents that, which accounts for the freezing; it does not account
for a repo the session never visited. Worth establishing before any shell-side fix, because whatever
put it there will still be there afterwards.]

## Design

**Fix the shell, not the instruction.** Settled by the user 2026-09-18, against this plan's own
earlier preference for rewriting the rule to say `uv run`:

> uv run breaks our allowlist rules and has its own complexity, and also not all systems that use
> our skills necessarily use uv in all projects. unless this is our last resort, try to get direnv
> to be more reactive, somehow, and also see how we can avoid keeping an incorrect env when
> switching directories into another place with a different direnv setup or none at all.

[DECISION: **`uv run` is rejected as the standing instruction, and the allowlist reason is the one
that settles it.** Every rule in `~/.claude/settings.json` matches on a literal command prefix, so
`uv run pytest` matches none of the `Bash(pytest:*)`-shaped grants and every venv-tool call would
start prompting. The other two reasons stand on their own: `uv run` carries its own resolution
behaviour, and the skills this machine publishes are used on machines that need not have uv at all,
so a rule written around uv is a rule that stops being true off this box.]

### The mechanism, measured rather than reasoned about

`eval "$(direnv export zsh)"` in `~/.zshenv`, guarded on `CLAUDECODE`, declared through
`[packages.claude-code]` beside the `PIPE_FAIL` snippet that already relies on the same property —
`setup.toml` documents it at the block: each Bash call is a non-interactive `zsh -c`, so `~/.zshenv`
is read **every** call while `~/.zshrc`, where direnv's real hook lives, is read once per session.

All four rows measured 2026-09-18 on direnv 2.32.1, from a session whose frozen environment belonged
to `power-user-linux-setup`:

| scenario                                                        | result                                                                       |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| cwd is another repo with an allowed `.envrc` (`olx-polite-mcp`) | **switches** — `DIRENV_DIR`, `VIRTUAL_ENV` and `ruff` all become that repo's |
| cwd has no `.envrc`                                             | **unloads** — emits `unset DIRENV_DIR` and restores the prior `PATH`         |
| cwd has a blocked `.envrc`                                      | unloads the previous env; writes a red error to stderr unless silenced       |
| cost                                                            | ~21 ms per call (five runs in 0.105 s)                                       |

The first two rows are the two halves of the ask, and both are satisfied by the same one line.

```sh
if [ -n "${CLAUDECODE:-}" ]; then
  setopt PIPE_FAIL
  export REPO_TASKS_RUN_REPORT=1
  if command -v direnv > /dev/null 2>&1; then
    eval "$(DIRENV_LOG_FORMAT= direnv export zsh)"
  fi
fi
```

[PITFALL: **the `command -v` guard must be an `if`, not a `&&`.** `setup.toml` already records why
for the existing block: `~/.zshenv` is read on every zsh invocation, so a trailing `&&` whose left
side is false leaves the file's last status non-zero in **every** shell. The guard itself is not
optional either — direnv is `[packages.direnv]`, a separate package a tag profile can exclude, while
this snippet ships with `[packages.claude-code]`.]

[DECISION: **`DIRENV_LOG_FORMAT=` rather than `2>/dev/null`.** Measured: the empty log format
silences direnv's own output completely, the redirect would be a second mechanism doing the same
job, and one of them would eventually be removed as redundant by someone who did not know which. The
cost is real and is accepted below.]

### What silencing costs, and why it is still right

A blocked `.envrc` — the state of every freshly cloned repo until someone runs `direnv allow` — now
produces no venv and no explanation. The agent sees `command not found`, which is at least honest,
where the unsilenced alternative is a red direnv error on **every** Bash call in that repo.

That is acceptable only because the remedy already exists and is already documented:
`inv
dev-env.setup` runs `uv sync` and `direnv allow` together, and `tests/README.md` names it as
the once-after-cloning step. The instruction change this plan still owes is therefore small — not
"use `uv run`", but "if a venv tool is missing, run `inv dev-env.setup`".

### The gap this does not close

[PITFALL: **`cd <other repo> && <command>` in one call is unaffected, and that is the shape
`~/.agents/AGENTS.md` sanctions for cross-repo work.** `~/.zshenv` is sourced at shell startup,
before the command's own `cd` runs, so the export resolves the _starting_ directory. Measured: from
`power-user-linux-setup`, `zsh -c 'eval "$(direnv export zsh)"; cd …/olx-polite-mcp && which ruff'`
still answers with `power-user-linux-setup`'s `ruff`. The cross-repo section's existing advice — use
the tool's own directory-scoping option, or the target repo's `.venv/bin` by absolute path — stays
correct, and only its stated reason changes.]

That also answers this plan's third question in the safe direction: the hook makes the _bare command
in another repo's cwd_ better rather than subtler, because that case now resolves to the repo you
are standing in. Nothing that section warns about becomes wrong; one sentence of its reasoning does.

### The `ingesta` entry, explained

Running `direnv export zsh` from a directory with no `.envrc` prints the `PATH` it would restore to,
and that baseline **already contains `ingesta/.venv/bin`** — along with `~/.local/bin` three times
and `go/bin` twice. So direnv did not add it and the hook will not remove it: it is in the
environment the session snapshot captured, before any `.envrc` was applied.

[DECISION: **that is a separate defect and is not fixed here.** It predates the hook and survives
it. Worth its own plan once someone establishes how a never-visited repo's venv reached a captured
snapshot — the duplication in the same `PATH` suggests accumulation across shells rather than
anything direnv did.]

### How many repos are affected

Swept 2026-09-18 across `~/projects/github.com-personal`, 22 git repos:

- **7 have an `.envrc`** — `agent-skills`, `ingesta`, `invoke-stubs`, `olx-polite-mcp`,
  `power-user-linux-setup`, `repo-tasks`, `scaffoldapy`. These are the ones the hook helps.
- **2 have a venv and claim direnv in their own `AGENTS.md` while having no `.envrc`** —
  `freshful-polite-mcp` (already known, being fixed in that repo) and **`temu-polite-mcp`**, which
  this plan did not know about. A missing `.envrc` is a separate defect from the hook, and the hook
  does not paper over it: those two get `command not found` either way until the file exists.
- `invoke-stubs` has the file and does not claim it — the harmless direction.

## Files touched

| file                                      | change                                                                                  |
| ----------------------------------------- | --------------------------------------------------------------------------------------- |
| `setup.toml`, `[packages.claude-code]`    | the `direnv export` line inside the existing `CLAUDECODE` guard                         |
| `config/agents-md/` (the owning fragment) | the venv-tool rule stops asserting the bare command resolves; names `inv dev-env.setup` |
| `config/agents-md/` (cross-repo section)  | one sentence of reasoning, per the gap above — the advice itself is unchanged           |
| `contributing/session-environment.md`     | the measured table: what the hook does per scenario, and the `cd … && …` gap it leaves  |

Deployed by `inv zsh.configure` for the snippet and `inv deploy.all --name agents-md` for the rules.
Neither is a file to edit under `~` by hand.

[PITFALL: **this change is live for every parallel session on the next command, with no restart.**
`~/.zshenv` is read per call, which is the property the whole design rests on and is also what makes
deploying it mid-session an action with reach beyond this one. `contributing/session-environment.md`
already records the measured difference between `~/.zshenv` and `~/.zshrc` here; this is the first
change to exploit it deliberately.]

## Verification

Re-run the measurement that produced the table above, from a Bash call rather than reasoned about:

- **In a repo with an allowed `.envrc`**: `echo $DIRENV_DIR` names _that_ repo, and `which ruff`
  resolves inside its `.venv`.
- **After a plain `cd` to a second such repo** (the harness's own tracked cwd, not a chained `cd`):
  both answers change to the second repo. This is the row that did not work before.
- **In a directory with no `.envrc`**: `DIRENV_DIR` is unset and no repo's `.venv/bin` is on `PATH`.
- **In a repo with a blocked `.envrc`**: no direnv output on any call, and `inv dev-env.setup` is
  what resolves it.
- **The status trap**: `zsh -c 'true'` still exits 0 on a machine with no direnv installed, which is
  what the `if` guard is for and what a `&&` would break.

Filed from a session in `freshful-polite-mcp`, which cannot edit this repo; the design above was
settled and measured here.
