---
status: idea
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

## Open questions

[NEEDS CLARIFICATION: fix the shell, or fix the instruction? These are different projects. Making
direnv actually fire for Bash-tool calls means exporting its environment in whatever `zshenv`
snippet the harness's shell sources — plausible, since `[packages.claude-code]` already ships one
for `PIPE_FAIL`, guarded on `CLAUDECODE`. Fixing the instruction means rewriting the rule to say
"always `uv run` in an agent session" and deleting the premise. The second is a five-minute edit
that is true immediately; the first removes the friction the rule was trying to spare and is the
better end state.]

[NEEDS CLARIFICATION: if the shell is fixed, is `direnv export zsh` the right mechanism, and is it
safe to run per-call? It reads `.envrc` and emits an environment; it also refuses an unauthorised
directory, which is the common case for a freshly cloned repo and would need to fail quietly rather
than noisily. `direnv exec <dir> <cmd>` is the per-command alternative and needs no hook at all, but
it changes the shape of every command an agent types, which is the thing the rule was avoiding.]

[NEEDS CLARIFICATION: does fixing the hook break the cross-repo rule that depends on it? "Running a
command against a different repo" warns that a bare `pytest`/`inv` against another repo silently
runs the primary project's interpreter, and its stated reason is that direnv does not fire. If
direnv starts firing per-call on cwd, that failure mode changes shape — possibly for the better,
possibly into something subtler. Re-read that section as part of this change rather than after it.]

[NEEDS CLARIFICATION: how many repos are actually affected, and is a missing `.envrc` a separate
defect? 7 of the personal repos have one; `freshful-polite-mcp` does not, while its own `AGENTS.md`
claims "direnv auto-activates it". That repo's own drift is being fixed in that repo. Worth a sweep
to see whether others make the same claim without the file.]

## Recommended direction

Do the instruction fix now and the shell fix deliberately, in that order — the instruction is wrong
today and every agent session on this machine reads it.

For the wording, the rule should end on the command that replaces the habit rather than on a
premise: in an agent session, `uv run <tool>` is the default for a venv tool. That also makes it
consistent with the cross-repo section's parenthesis instead of contradicting it.

[PITFALL: **the original wording of this section said `which` is "worth running only when something
surprising happens", and the correction above makes that the one sentence not to write.** `which`
does not fail in the interesting case. It returns a real, plausible, absolute path to a real tool —
belonging to whichever repo the session started in — and nothing about the answer says so. A reader
told to trust `which` until surprised will never be surprised, because the wrong answer looks
exactly like the right one. If the rule mentions `which` at all it has to say what to compare the
answer _against_: the repo you are standing in.]

Then decide the shell question on its own merits. If the hook is made to fire, this rule gets
rewritten a second time, which is cheap and is the right order: an instruction that matches reality
today beats one that anticipates a change nobody has made.

Filed from a session in `freshful-polite-mcp`, which cannot edit this repo.

## Verification

Not started. The check is the measurement above, re-run after whichever fix lands: from a Bash call
in a repo with `.envrc`, `echo $DIRENV_DIR` and `which ruff`. For the instruction-only fix, the
verification is instead that the rule no longer asserts the bare command resolves.
