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

[DECISION: **it is `grep`'s flag string carried over whole, which is the belief hypothesis rather
than the keystroke one.** The distribution is `-rn` × 27, `-ril` × 3, `-rln` × 1, `-rl` × 1, and not
one bare `-r`. That was first read here as closing the belief hypothesis — **wrongly**, and the
correction is the useful part: a `grep` user rarely wants recursion _alone_, so a believer bundles
too, and the absence of bare `-r` is what belief predicts rather than evidence against it. The check
that settles it is what `grep` itself is typed as in the same corpus — `grep -rn` 118×/week,
`grep -rln` 12×, `grep -rlF` 11×. **Every defective `rg` bundle is a `grep` bundle in daily use on
this machine.** So the fix is a translation, and wording can carry a translation.]

[PITFALL: **bare `rg -r <pat> <path>` does not look broken — it looks like the recursive search the
user wanted, which is why the belief survives contact with the output.** `-r` takes `<pat>` as the
replacement, so `<path>` becomes the pattern and, with no path argument left, rg searches the whole
working directory. Probed 2026-09-05: `rg -r config_path sample.txt` in a directory containing
`sample.txt` returned fourteen hits **from a different file entirely**, each with the search term
written over the match. Recursive, non-empty, and containing the string searched for. Exit 0. This
row is absent from the week's corpus, so the rule now covers a form nobody has yet been caught by —
included deliberately, because it is the form whose output would be believed.]

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

## The wording attempt, 2026-09-05

The clause in `config/agents-md/bash.md` was rewritten rather than the mechanism reached for,
because the measurement above says the habit is a translation error and the old wording never
addressed the shape that occurs.

[DECISION: **the old clause failed on three specific things, not on volume.** Its worked example was
`rg -r <pat> <path>` — the one form that does not appear in the corpus at all — so a reader
pattern-matching on the example was warned about a shape nobody types and told nothing about `-rn`.
It was a prohibition rather than a substitution, against this corpus's own finding that the
strongest form of a rule is the command replacing the habit (the `gh run watch` case in
`contributing/global-agents-md.md`). And it gave no detection signature, which is why all three
occurrences on record were caught by the accident of the searched string being conspicuously absent
from its own results.]

[DECISION: **the replacement is one edit — delete the `r`, keep every other letter — plus a table of
the six real forms and a detection signature.** Stated as an edit it is exercised on every
`grep`→`rg` translation, which is ~150 a week, rather than firing only at the moment of the
accident; that is the structural difference from the four `head`/`tail` rewordings, each of which
restated the same prohibition at a different trigger. Whether that difference matters is exactly
what the next count tests.]

[UNVERIFIED: whether this moves the rate. Baseline is
`~/.local/state/session-bash-audit/2026-09-05-pipefail-live.json` (32 real defective calls, 21
sessions, 1.2% of `rg` invocations); re-count with `audit.py --days 7 --compare` after a week, and
correct for the counter's ~8% prose over-report until that is fixed. If it has not moved, the
`ask`-rule below is the fallback and the wording lever is spent for this rule too.]

## Open questions

[NEEDS CLARIFICATION: **which mechanism, if the wording attempt above does not move the rate.**
Three candidates, and the choice is a real trade-off rather than an obvious pick:

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

The measurement asked for is done, and it named a translation habit rather than a stray keystroke —
so the wording lever was not spent after all, and the rewritten clause is the cheap, reversible test
of it. Re-count in a week against the baseline named above. If the rate holds, the `ask`-rule is the
fallback: it is the only one of the three mechanisms that needs no standing rule bent to allow it,
and its cost is one prompt on a shape occurring about four times a week.
