---
status: landed
updated: 2026-09-12
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

## Answered (2026-09-11)

**Nothing else on the machine asserted 120.** Two hits across the fragments and the evidence page,
both the same clause — the fragment stating it and the evidence page summarising it — so the edit
was one place and its summary, with no third copy to drift.

**The list of codes stays, and the question resolves the opposite way from how it was asked.**
Adding the guarded case makes it four codes for one meaning, which is the argument _for_ keeping
them rather than against: the clause now says outright that the number is not the thing to read. A
reader who acts on the sentence never has to tell 141 from 120; a reader who wants to check the
claim still can, which is this corpus's standard.

## Recommended direction

One clause, in `config/agents-md/`'s verification fragment: keep 120 for Python generally, add 141
for a script that handles SIGPIPE, and name `agent-skills`' scripts as the set that does. Then
`inv deploy.all --name agents-md`.

The measurement worth carrying across with it, since it is what the whole passage is about: over the
30 days to 2026-09-08, **9,224 Bash calls were tagged `head/tail` and 9 of them actually cut
output** — 0.10%. The cost of the habit is the re-run and the masked exit code, not lost bytes. It
is recorded in `agent-skills`' `skills/session-bash-audit/references/research.md`.

## Migrated to

- `config/agents-md/verification.md`, the "Reading a command's result" bullet — the guarded case
  added alongside 120 rather than replacing it, deployed with `inv deploy.all --name agents-md`.
- [`contributing/global-agents-md.md`](../contributing/global-agents-md.md), "Reading a command's
  result" — the before/after exit table, the pitfall about why 120 could not be swapped out, and the
  9-in-9,224 truncation rate the whole passage rests on.

Deliberately not migrated: the list of the ten scripts by name. It was true on 2026-09-08 and is a
maintenance burden the moment a script is added; the clause names the directory instead, and
`rg -l SIGPIPE ~/.agents/skills/*/scripts/*.py` is the current answer.
