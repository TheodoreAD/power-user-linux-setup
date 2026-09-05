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

[UNVERIFIED: whether the piped-gate _rate_ moves. Baseline saved as
`~/.local/state/session-bash-audit/2026-09-05-pipefail-live.json`, to be read with
`audit.py --compare` after a week. Truthfulness is the goal and is already achieved; a rate change
would be a bonus, not the test.]

[PITFALL: `audit.py --save-baseline` with no path silently destroyed the pre-`bba2ed9` baseline —
its default filename is a UTC date, and at 02:13 local (+03:00) that is the previous day's name.
Reconstructed from the transcripts and filed against the skill as
`agent-skills/2026-09-05-save-baseline-overwrites-silently.md`; pass an explicit path meanwhile.]

## Remaining

Layers 2 and 3 are other repos' work and are not this plan's to do: 3 is `agent-skills`' own
scripts, 2 is the `repo-tasks` quiet gate. Order across repos was decided 2026-09-05 as 1 (this),
3, 2.
