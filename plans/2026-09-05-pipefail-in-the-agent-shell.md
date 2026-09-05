---
status: in-progress
updated: 2026-09-05
source_repo: github.com-personal/agent-skills
source_session: 4e6fc3cc-eebb-4ea1-b035-ca0112dc9982.jsonl
source_moment: 2026-09-04T22:17:38Z
---

# `pipefail` in the agent's shell, and the Bash rule that stops being true

## Context

Layer 1 of `agent-skills`' `plans/2026-09-05-a-piped-gate-that-cannot-lie.md`, which owns the design
and the measurements. The decision it rests on, taken with the user 2026-09-05: the fix for the
`head`/`tail` rule is **not a rule**. Four rewordings since 2026-08-24 were each measured afterwards
and none moved the rate; the newest, deployed 2026-09-04 14:26 (`bba2ed9`), has four sessions after
it at 50%, 6%, 15% and 25% — inside the spread sessions already had. The watch in this repo
(`plans/2026-08-23-global-agents-md-adherence-watch.md`) has said "adherence, not wording" since its
session 5; this is the mechanism that replaces the sentence.

Over the seven days to 2026-09-05 (60 main sessions, 14,611 Bash calls), 2,109 calls ended in
`| tail` and 812 of the 1,396 `inv quality.*` runs were piped — 58% machine-wide, 41% in this repo's
sessions. Every one of those returned `tail`'s exit status, which is 0 whatever the gate did.

## What to do

**One `zshenv` snippet on `[packages.claude-code]` in `setup.toml`**, beside `claude_default_mode`,
deployed by the existing `zsh.configure` block writer:

```shell
# The Bash tool runs each call as a non-interactive `zsh -c`, i.e. a script. Scripts get pipefail:
# a `| tail` then carries the upstream exit code instead of tail's 0.
[ -n "${CLAUDECODE:-}" ] && setopt PIPE_FAIL
```

Scoped to the agent's shell on purpose (decided with the user): `[[ -o interactive ]]` would also
change exit statuses for cron, IDE task runners and every `zsh -c` nobody audited. A second guard
per harness is added as harnesses are.

**Why it reaches every call, read from the live harness 2026-09-05.** Each Bash call is
`/usr/bin/zsh -c 'source ~/.claude/shell-snapshots/<snapshot>.sh … && setopt NO_EXTENDED_GLOB
NO_BARE_GLOB_QUAL … && eval '<cmd>''`
— no `-f`, `norcs` unset, `login` set — so `~/.zshenv` is read first on every call. The snapshot
ends with one `setopt <name>` per option captured from the interactive shell and unsets nothing, so
`PIPE_FAIL` survives it. `CLAUDECODE=1` is exported into every call.

**Probed under `setopt PIPE_FAIL` in a child zsh, same machine:** `(exit 3) | tail -1` → 3; a
failing `pytest … 2>&1 | tail -1` → 4; `inv quality.lint-check 2>&1 | tail -1` → 0; `rg | tail`,
`git log | tail` → 0. `git log | head -1`, `ls -R | head -1`, `cat f | head -1` → 141 (SIGPIPE);
`rg … | head -1` with more matches than shown → 1; a Python script cut by `head` → 120 plus the
traceback it already prints today; `fd | head` → 0. So a `| head` returns non-zero exactly when it
cut something, which is the data-loss event the rule has been describing in prose.

**Then rewrite the rule whose reason this removes.** `config/agents-md/verification.md`, "Reading a
command's result", says "a pipe masks the exit code" as the reason not to pipe; under pipefail that
is false, and `session-bash-audit`'s routing table names this case — the rule's source is rewritten,
not restated louder. The replacement is a fact rather than a composition rule: a non-zero exit after
`| head` means `head` cut the output, so count first (`rg -c`, `wc -l`) or run it whole;
`| rg`/`| grep` as a last stage returns 1 on no match. The `| tail` half of `bash.md`'s "Composing a
Bash call" gate paragraph (added `bba2ed9`) can shrink to its data-loss cost — the 2,109 `| tail`
calls a week become truthful, so the sentence that was fighting them has less to carry. Evidence
into `contributing/global-agents-md.md` under both headings, with the probe table.

**Passes "Proposing an enforcement mechanism", and say so there.** It does not correct, rewrite or
block anything the agent typed and fires nothing behind its back; it makes the shell report what
happened, which is what `shellcheck` and every shell style guide already ask of a script. Developers
get the same treatment in their scripts.

## Evidence

- Design and measurements: `agent-skills` `plans/2026-09-05-a-piped-gate-that-cannot-lie.md`.
- The user's framing, 2026-09-05, in the `agent-skills` session named above: _"ruminate deeply on
  how we can solve this, it's disruptive and can lie about a lot of things."_
- Harness invocation line: `ps -o args= -p $$` inside a Bash call, 2026-09-05; the snapshot's option
  block is the last 22 lines of `~/.claude/shell-snapshots/snapshot-zsh-1788557935829-*.sh`.
- The watch's own `[UNVERIFIED:]` after `bba2ed9` asked for a `--compare` against
  `~/.local/state/session-bash-audit/2026-09-04.json`; the four post-deploy sessions above are that
  answer at n=4, and a week of them should be reported before the wording is judged.

## Verification, 2026-09-05

Landed in three commits: the snippet on `[packages.claude-code]`, the rule rewrite across
`config/agents-md/bash.md` and `verification.md`, and the evidence into
`contributing/global-agents-md.md` under both headings. `inv zsh.configure` wrote the block,
`inv deploy.all --name agents-md` regenerated `~/.agents/AGENTS.md`.

The end-to-end `[UNVERIFIED:]` is **answered**, and in the deploying session itself — `~/.zshenv` is
re-read on every Bash call, so no restart was needed and a snapshot captured before the change made
no difference. `setopt | rg pipefail` returns `pipefail`; `(exit 3) | tail -1` reports 3;
`pytest <no such test> 2>&1 | tail -2` surfaced exit 4 where it would previously have read as
success. The `| head` side behaves as the child-zsh probe predicted — 141 for a SIGPIPE'd `git log`,
1 for a truncated `rg`, 0 for an untruncated `ls`.

[UNVERIFIED: whether the piped-gate _rate_ moves. Compare against
**`~/.local/state/session-bash-audit/2026-09-05-pipefail-live-rescored.json`**, not the
`…-pipefail-live.json` this plan originally named. Truthfulness is the goal and is already achieved;
a rate change would be a bonus, not the test.]

[PITFALL: **the original baseline was written by a superseded instrument, and nothing in the file
says so.** It was saved at 02:14 local from the _installed_ `audit.py`, whose mtime shows the
re-install carrying `0165577` ("a pipe inside quotes is not a pipe") did not land until 18:44 the
same day — so the baseline predates the commit that changes what counts as a pipe, which is the
entire subject of this measurement. Re-scoring the same 7-day window under the current code moved
`exit-masked` **down** (2,383 → 2,323) and `head/tail` flat (3,765 → 3,767) while the call count
rose by 577, which is the quote fix removing false positives. A `--compare` straddling that commit
would credit the pattern change to `PIPE_FAIL`, in the direction that flatters it. Both baselines
are kept — overwriting the old one is a separate filed defect — and `agent-skills`'
`plans/2026-09-05-quiet-gate-changes-what-the-instruments-see.md` owns the general problem.]

[PITFALL: `audit.py --save-baseline` with no path silently destroyed the pre-`bba2ed9` baseline —
its default filename is a UTC date, and at 02:13 local (+03:00) that is the previous day's name.
Reconstructed from the transcripts and filed against the skill as
`agent-skills/2026-09-05-save-baseline-overwrites-silently.md`; pass an explicit path meanwhile.]

## The second export on the same snippet: `REPO_TASKS_RUN_REPORT`

Merged in 2026-09-05 from `2026-09-05-agent-shells-set-repo-tasks-run-report.md`, filed for this
repo from a `repo-tasks` session that did not know this plan existed
(`source_session: 86b6d25d-eb68-4751-b989-ad45931ef62a.jsonl`,
`source_moment: 2026-09-05T11:00:00Z`; that file is gone —
`plans.py archive --file 2026-09-05-agent-shells-set-repo-tasks-run-report.md` reads it back). **It
is the same file, the same guard and the same population**, and the two lines are complementary
halves of one lie: `PIPE_FAIL` makes a piped gate **exit** non-zero, report mode makes its last
three lines **say which command failed**. Neither substitutes for the other. The name of this plan
is kept rather than widened because `agent-skills` and `repo-tasks` plans cite it by filename and
this repo may not edit theirs.

`repo-tasks` gained an opt-in agent output mode on 2026-09-05 (`d322392`..`7db8b29`): with
`REPO_TASKS_RUN_REPORT` set, every command run with `echo=True` collapses to one delimited line with
its output folded on success and replayed whole on failure, and a gate ends with a verdict line.

```
ruff check . | ok | 0.0s | All checks passed!
basedpyright | ok | 2.5s | 0 errors, 0 warnings, 0 notes
pytest | ok | 1.4s | 592 passed in 1.27s
quality.precommit | PASS | 15 steps | 4.6s
```

With the variable unset, the package touches invoke's config not at all and `inv` behaves exactly as
invoke documents. **Nothing sets the variable, so nothing is in that mode** — which makes the
`repo-tasks` change a net regression against the measurement that motivated it until this half
lands: the reporting exists and no agent session sees it.

**The measurement is the same one this plan opens on, read from the other end.** `repo-tasks`'
`contributing/quality-gate.md`, "What the gate prints": over the seven days to 2026-09-05, across
every consumer, **812 of 1,396 `inv quality.*` runs — 58% — were piped through `head`/`tail`**, 466
of them asking for the last few lines of a roughly 50-line success. Every one of those runs was an
agent session, because the corpus is agent transcripts. That is the fact the change turns on.

The first design there made folding the **default**, and the user rejected it on the rule of least
surprise — without the env var everything runs normally, with it the runner is overloaded. Both
positions hold at once, and **this repo is where they are reconciled**: the variable is set by the
environment for agent shells, so no session has to reach for anything, while a human at a terminal
and a CI runner keep stock invoke. ("Flip the default" and "reach the population" looked like the
same lever and were not — the general form of that lesson is
[`2026-09-05-least-surprise-is-not-written-down-anywhere.md`](2026-09-05-least-surprise-is-not-written-down-anywhere.md).)

The change is one line beside the `PIPE_FAIL` one, under the same `CLAUDECODE` guard:

```shell
export REPO_TASKS_RUN_REPORT=1
```

### Verification for that half

- `env | rg REPO_TASKS_RUN_REPORT` in a fresh agent Bash call returns it set; unset in an
  interactive human shell.
- `inv quality.precommit` here then prints report lines and a verdict for an agent, and invoke's own
  streaming output for the human.
- End to end with layer 1: `inv quality.check 2>&1 | tail -3` on a failing gate ends with
  `FAIL | <command> | exit=<n> (output above)` **and** the Bash tool reports a non-zero exit.

[NEEDS CLARIFICATION: whether the guard stays `CLAUDECODE` or widens. The variable is useful to any
agent harness, `CLAUDECODE` is the only such marker this machine sets, and inventing a broader
condition with nothing to test it against is worse than a narrow one that works. Recommend keeping
the existing guard and widening when a second harness actually appears — the same call this plan
already makes for `PIPE_FAIL`.]

[NEEDS CLARIFICATION: whether this repo's own CI should set it. Recommend **no** — a GitHub Actions
log is scrolled by a human reading a failure, and full streaming is what belongs there. Recorded
because it will be asked.]

[DEFERRED: this repo pins `repo-tasks`, so report mode does nothing here until that bump lands.
`repo-tasks`' `contributing/consumer-sweep.md` owns that sequence, and the batched sweep is
`repo-tasks`' `plans/2026-08-25-consumer-transitions.md`.]

## Remaining

Layers 2 and 3 are other repos' work and are not this plan's to do: 3 is `agent-skills`' own
scripts, 2 is the `repo-tasks` quiet gate. Order across repos was decided 2026-09-05 as 1 (this),
3, 2.
