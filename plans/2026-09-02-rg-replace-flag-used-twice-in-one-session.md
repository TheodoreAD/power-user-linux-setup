---
status: idea
updated: 2026-09-02
---

# `rg -r` was used twice in one session, by a session that had already caught it

## Context

`~/AGENTS.md` carries the rule, under "Viewing, searching, or editing files":

> Do not carry `grep -r`'s flag across with the habit: `rg` is recursive by default and its `-r` is
> `--replace`, so `rg -r <pat> <path>` silently prints matches with the matched text **rewritten** —
> plausible-looking output that is not what the file says.

An `ingesta` session on 2026-09-02 violated it **twice**, three hours apart, with the rule in
context the whole time.

**First occurrence**, searching a vendored reference clone:

```shell
rg -rn --no-heading -i "overdue|is_late|isLate|missed|skipped" "$RESEARCH_HOME/repos/.../src"
```

`-rn` was parsed as `-r n`, so every match printed with the matched text replaced by `n` —
`takenLabel.label = _('n');`, `.status-n { color: … }`. The session noticed, said so to the user,
named the rule, and re-ran without `-r`. Exactly the intended outcome.

**Second occurrence**, three hours later, during that session's own harvest:

```shell
rg -rn --no-heading -i "ripgrep|rg -r|--replace" /home/tdumitrescu/plans 2>/dev/null | head -10
```

It returned nothing. That is consistent with "no matches" and also with a mangled search, and the
session could not tell which without re-running — which it did, correctly, getting the same empty
result.

## Why this is worth a plan rather than a shrug

**The wording is not the problem.** The rule states the constraint, names the mechanism, and gives
the failure mode. It was read, understood, and cited out loud by the very session that then repeated
the mistake. So this is the third of the three shapes `session-harvest` distinguishes — not a rule
that is wrong, and not one that was reasoned around, but one **simply not followed**, which it calls
a measurement question rather than a rewording one.

**The second occurrence is the interesting one**, and it has a specific shape worth naming: it
happened while the session was searching for prior art _about this very trap_. Whatever mechanism
produces `-rn` is evidently not reached by having just written a paragraph about it.

**What makes it costly is that a mangled search looks like a clean one.** Both occurrences returned
plausible output — the first plausible-but-wrong, the second plausible-and-empty. Neither errors,
neither warns, and an empty result is exactly what a session reads as "nothing owns this finding",
which is the conclusion it was being used to draw.

## Open questions

[NEEDS CLARIFICATION: **Whether `-rn` specifically is the shape to measure**, rather than `-r` in
general. Both occurrences here were `-rn`, and the hypothesis worth testing is that it is a typo for
`-n` with `r` reaching for `grep -r`'s recursion — which would make it a keystroke habit rather than
a belief about the flag, and would predict `-rn`/`-rin` dominating over a bare `-r`.]

[NEEDS CLARIFICATION: **Whether `session-bash-audit` should count it.** It has counters for
`find-not-fd` and `sed-n`, so an `rg-replace` counter is the same kind of thing and would answer
whether this is one session's tic or a machine-wide rate. That skill invites newly noticed
anti-patterns explicitly, so the addition belongs there; this plan is the evidence for it. Note the
counter has to match the flag _as parsed_ — `-r`, `-rn`, `-rin`, `--replace` — rather than the
literal string `-r`.]

[NEEDS CLARIFICATION: **Whether an alias or a wrapper is the honest fix**, given the machine's own
standing preference for teaching over silent correction. `~/AGENTS.md` says to prefer teaching the
agent what to run over a mechanism that fires behind its back — and this is a case where the
teaching demonstrably did not take, twice, in three hours. That is an argument for measuring first
rather than for reaching straight for the wrapper.]

## Recommended direction

Measure before changing anything. Add the counter to `session-bash-audit`, run it over the existing
transcript corpus, and see whether this is one session or a rate. If it is a rate, the interesting
question is which of the two hypotheses above it fits, because they have different fixes.
