---
status: idea
updated: 2026-09-08
---

# `~/AGENTS.md` says 120 for a cut Python script, and that stopped being true today

## Context

`~/AGENTS.md`'s "Reading a command's result" documents the exit codes a truncating pipe produces,
and it is the passage a session reads when a `| head` comes back non-zero:

> **A non-zero exit after `| head` means `head` cut something off**, not that the command failed —
> 141 for a `git log` killed by SIGPIPE, 1 for an `rg` with more matches than shown, 120 for a
> Python script cut mid-write.

That reading is measured and correct as written. **The 120 clause is now stale for one family of
scripts**, and the family is the one an agent session runs most: every entry point under
`agent-skills`' `skills/*/scripts/` handled SIGPIPE as of 2026-09-08, so a cut `plans.py`,
`audit.py`, `fitness.py`, `harvest.py`, `library.py`, `trigger.py`, `prompts.py`,
`package_health.py`, `count_shapes.py` or `find_mutations.py` now dies on the signal and returns
**141**, not 120.

Filed rather than edited: a session in `agent-skills` does not write to this repo.

## Evidence

Measured on `audit.py --days 30 --samples 40`, whose output exceeds the 64 KB pipe buffer, so the
reader closes the pipe while the writer is still writing:

| run                        | exit    | stderr                                                         |
| -------------------------- | ------- | -------------------------------------------------------------- |
| guard bypassed (as before) | **120** | `Exception ignored while flushing sys.stdout: BrokenPipeError` |
| with the guard (now)       | **141** | clean                                                          |

The change is `signal.signal(signal.SIGPIPE, signal.SIG_DFL)` inside each `__main__` guard — layer 3
of `agent-skills`' `plans/2026-09-05-a-piped-gate-that-cannot-lie.md`, whose point is that a cut
pipe should report as a cut rather than as a crash.

[PITFALL: **120 does not disappear from the machine, so the clause cannot simply be swapped.** It is
still what any _other_ Python program does when cut — anything not carrying this guard, which is
most Python on the machine, `inv` included. Two of the nine real truncation events measured over the
30 days to 2026-09-08 were `inv quality.precommit 2>&1 | head -20` at exit 120, and `inv` is not one
of these scripts. So the honest edit adds 141 as the guarded case rather than replacing 120.]

## Open questions

[NEEDS CLARIFICATION: is the exit-code list worth keeping at that level of detail at all? Its
working half is the sentence before it — a non-zero exit after `| head` usually means `head` cut
something off. The three codes are the evidence for that sentence, and a reader who acts on the
sentence never needs to tell 120 from 141. Against dropping them: the codes are what makes the claim
checkable, and this repo's own standard is that a rule with a measurement attached survives review.]

[NEEDS CLARIFICATION: does anything else on the machine assert 120? A grep of
`contributing/global-agents-md.md` and the `config/agents-md/` fragments would say, and the fragment
is the file to edit rather than the deployed `~/AGENTS.md`.]

## Recommended direction

One clause, in `config/agents-md/`'s verification fragment: keep 120 for Python generally, add 141
for a script that handles SIGPIPE, and name `agent-skills`' scripts as the set that does. Then
`inv deploy.all --name agents-md`.

The measurement worth carrying across with it, since it is what the whole passage is about: over the
30 days to 2026-09-08, **9,224 Bash calls were tagged `head/tail` and 9 of them actually cut
output** — 0.10%. The cost of the habit is the re-run and the masked exit code, not lost bytes. It
is recorded in `agent-skills`' `skills/session-bash-audit/references/research.md`.
