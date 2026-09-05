---
status: idea
updated: 2026-09-05
---

# `rg -r`: 32 defective calls a week, and never once the bare flag

Opened on two occurrences in one `ingesta` session; a third arrived from a different repo the same
day. The corpus-wide count that resolved it is in "Measured, 2026-09-05" below — the filename and
the three-occurrence framing above it are kept as written, since plan-docs promotes in place and the
original hypothesis is worth reading beside the number that confirmed it.

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

**Third occurrence, 2026-09-02, this repo**, in a session working through the `~/AGENTS.md` plan
cluster — so a session that had the rule in context, was reading plans _about_ the rule, and had
this very file open minutes earlier:

```shell
rg -rn 'check-rule-prerequisites' --glob '!plans/**' . 2>/dev/null | head -20
```

The output came back naming `inv ai.n` in four files, where every one of them says
`inv ai.check-rule-prerequisites`. It was caught immediately, because `ai.n` is not a plausible task
name and the searched string was conspicuously absent from its own results — the same accident that
saved the first occurrence, not a method. Had the pattern been anything the eye did not expect
echoed back, the corrupted output would have been read as fact, and it was being used to decide
whether a rule's rationale had a documented home.

Two things it adds. It is the **third `-rn`** out of three, which is now the whole sample and
supports the keystroke hypothesis over the belief one. And it happened in a different repo and a
different session from the first two, so this is no longer one session's tic.

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

## Measured, 2026-09-05 — it is a rate, and the keystroke hypothesis is confirmed outright

`session-bash-audit` grew the `rg-replace` counter, so the first open question below is answered by
its existence. Seven days of transcripts, 13,754 Bash calls: **39 tagged, of which 32 are real
defective invocations** — spread across **21 distinct sessions and 4 repos** (`ingesta` 14,
`repo-tasks` 7, this repo 6, `agent-skills` 5). Not one session's tic. Against ~2,590 `rg`
invocations in the same window it is **1.2%** — low-rate, persistent, and machine-wide.

[DECISION: **it is a typing accident, not a belief, and the corpus is unanimous.** The prediction
was that `-rn` would dominate a bare `-r`. It did better than that: **there is not one bare `-r`
misuse in the whole week.** Every single defective call is a bundle in which `-r` swallowed the
letters of the flag actually wanted — `-rn` × 27, `-ril` × 3, `-rln` × 1, `-rl` × 1. Nobody on this
machine thinks `-r` means recursive; the finger types `r` ahead of the flag it meant. That closes
the belief hypothesis, and with it every fix that works by explaining the flag.]

[PITFALL: **the cost is bigger than "the matched text is rewritten", which is all the rule says.**
`-r` consumes the rest of the bundle as its replacement string, so **the flags the caller asked for
never take effect at all** — and that is invisible in the output:

| as typed | replacement | what was silently dropped | what the caller gets                              |
| -------- | ----------- | ------------------------- | ------------------------------------------------- |
| `-rn`    | `n`         | `-n`                      | matches rewritten to `n`, **and no line numbers** |
| `-rl`    | `l`         | `-l`                      | rewritten lines instead of a file list            |
| `-rln`   | `ln`        | `-l`, `-n`                | same, no line numbers either                      |
| `-ril`   | `il`        | `-i`, `-l`                | case-**sensitive** search, lines not filenames    |

Measured live on the corpus's own `-ril` call —
`rg -ril "head/tail|exit-masked|exit code|piping a gate"` over three `plans/` directories returns
**116 rewritten lines**, where the intended `rg -il` returns **13 filenames**. The session that ran
it wanted "which files mention this", got lines, and piped them through `head -20`. Nothing about
116 plausible lines says the search was mangled.

The `-rn` row is the one that matters most by volume: a search whose whole purpose is a `file:line`
citation comes back with no line numbers, so either the citation is dropped or it is invented.]

[PITFALL: **the counter over-reports by ~8%, all in one direction.** 3 of the 39 are not
invocations: two `git commit -m` messages and one `plans.py commit -m` whose text quotes `rg -rn` or
names this very plan file. The regex anchors on `\brg\b` anywhere in the command rather than at a
command-segment boundary, so a corpus that writes _about_ this trap inflates its own count of it.
Filed against the skill, which owns the script; the 32 above is the corrected figure.]

## Open questions

[NEEDS CLARIFICATION: **which mechanism, now that wording is ruled out.** Three candidates, and the
choice is a real trade-off rather than an obvious pick:

- **An `ask` rule on the `rg -r` prefix**, generated by `cli-allowlist/`. It has a property that
  makes it fit unusually well: `rg -r` is a literal prefix of every defective bundle (`-rn`, `-ril`,
  …) and is **not** a prefix of `rg --replace`, so the accident prompts and the deliberate long-form
  spelling stays free. It is not a mechanism firing behind the agent's back either — the agent sees
  a prompt and the user sees the command, which `~/AGENTS.md` calls friction rather than
  prohibition. Against it: that pipeline classifies tools by _capability_ (read_only / write /
  dangerous), and `rg` is read-only however it is spelled. An ask-rule for a correctness trap would
  be the first entry that classifies by hazard-of-misreading instead, which is a new meaning for the
  file.
- **A shell function wrapping `rg`.** Rejected on the standing rule unless something changes: it
  corrects or refuses what the agent typed, which is the shape "Proposing an enforcement mechanism"
  exists to refuse. Worth noting the pipefail precedent does _not_ transfer — that made the shell
  report truthfully about a command it ran unaltered; there is no equivalent here, because `rg`
  genuinely did what the flags said.
- **Nothing, and accept 1.2%.** Defensible for `-rn`, whose output is conspicuously wrong (the
  searched string absent, `n` in its place) and which has been caught by eye all three times it was
  written up. Not defensible for `-ril`, whose output is 116 plausible lines.]

## Recommended direction

The measurement asked for is done and points one way: no wording change can help, because nobody
holds the wrong belief the wording would correct. Put the three mechanisms above to the user and
take the answer; the `ask`-rule option is the only one that does not need a rule bent to allow it,
and its cost is one prompt on a shape that occurs about four times a week.
