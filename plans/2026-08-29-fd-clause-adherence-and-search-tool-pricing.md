---
status: idea
updated: 2026-09-05
---

## Context

`~/AGENTS.md`'s "Viewing, searching, or editing files" rule ends with a tool- preference clause:
`rg` over `grep -r`, `fd` over `find`, with plain `grep`/`find` kept legitimate for non-recursive
lookups, `find -exec`/`-delete`, and portability. The user's standing impression, stated 2026-08-29,
is that agents do not respect it.

Measured over **15,171 Bash calls in 415 transcripts** under `~/.claude/projects/`:

| shape                                             | calls | share of that pair |
| ------------------------------------------------- | ----- | ------------------ |
| `rg`                                              | 2356  | —                  |
| `grep -r` / `grep -R`                             | 213   | **8%**             |
| `fd`                                              | 231   | —                  |
| `find`, plain lookup                              | 175   | **43%**            |
| `find` with `-exec`/`-delete`/`-mtime`/… (exempt) | 62    | —                  |

The impression is half right, and the two halves point opposite ways.

**`rg` adherence is good.** 92% of recursive text searches already use it. A rule holding at 92% is
not where effort belongs, and tightening its wording risks the "strengthen language rather than
lengthen explanation" trap in reverse — spending words on the half that works.

**`fd` adherence is bad.** 175 of 406 file-finding calls use `find` for a plain lookup. The samples
are not edge cases:

```
find . -name '*.py' -not -path './.venv/*' -not -path './.git/*' | sort
find . -iname "*plan*" -not -path "./.git/*"
find . -path ./.venv -prune -o -name '*.py' -print | sort
```

Each is `fd -e py` or `fd plan`, with the `.venv`/`.git` exclusions the author typed by hand
supplied free by `fd` being `.gitignore`-aware — which is the exact benefit the rule cites and the
exact work these calls are doing manually.

Two candidate causes, both in this repo's control:

1. **The clause buries `fd`.** It appears in a subordinate position inside a sentence about `rg`,
   after a long paragraph about the `rg -r`/`--replace` trap, and then hands out an exemption list
   ("`find -exec`/`-delete`, or portability") that 175 of 237 `find` calls do not qualify for. An
   exemption list adjacent to a preference reads as permission.
2. ~~**There is no price difference.**~~ **False when written, though not in the way first corrected
   here — see "The pricing lever" below.** The claim was that `~/.claude/settings.json` allows all
   four equally, so nothing in the permission layer distinguishes the preferred spelling from the
   discouraged one. It does not: `find` renders as **`ask`**.

## Re-measured 2026-09-05, with the rows step 1 asked for

The `agent-skills` change filed as step 1 landed: `session-bash-audit` now has separate
`grep-r-not-rg`, `find-not-fd` and `find-exempt` rows, so this is the first reading that is not a
hand-count. Seven days, 13,754 Bash calls:

| shape                    | calls | share of that pair |
| ------------------------ | ----- | ------------------ |
| `rg`                     | 2597  | —                  |
| `grep -r` / `grep -R`    | 150   | **5.5%**           |
| `fd`                     | 53    | —                  |
| `find`, avoidable        | 35    | **40%**            |
| `find`, genuinely exempt | 2     | —                  |

**Both halves held their position and neither moved.** `rg` 92% → 94.5%; `fd` 57% → **60%**. Nothing
was done to either clause in between — step 2 below was never executed — so this is stability under
an unchanged rule rather than an effect, and it is the control the sequencing was designed to
produce.

[DECISION: **the exemption list goes, replaced by a bar with the measurement in it.** The open
question below asked whether it should stay at all; the count answers it. Of 37 real `find` calls in
the week, **2** qualify — one `-printf`, one inside a `docker run` on an image with no `fd`. So the
carve-out protects 5% of calls while sitting adjacent to the preference for the other 95% to read as
permission, which is exactly the mechanism this plan hypothesised. It is not deleted outright,
because `find -exec`/`-delete` really is something `fd` does differently and a rule that is wrong
loses more than it gains. It is restated as a test — "acting on matches, selecting by time/size/
permission, `-printf`, or somewhere `fd` is not installed" — with **"2 of 37 qualified" in the rule
itself**, which converts a list that reads as an invitation into a bar that says your case probably
is not one.]

[DECISION: **`fd` gets its own sentence, in the translation form the neighbouring `rg -r` clause was
rewritten into the same day.** `find <dir> -name '*.py'` → `fd -e py . <dir>`. Same reasoning as
there: a substitution is exercised every time the tool is reached for, where a preference is only
consulted at the moment of doubt. The `rg` half loses its `fd` passenger and shrinks to one clause,
which is what a 94.5% rule should cost.]

[PITFALL: **`fd` prints nothing rather than erroring for a gitignored or dot-directory target**, and
the rule had advertised `.gitignore`-awareness purely as a benefit. Probed 2026-09-05 in this repo:
`fd activate` returns **0** hits and `find -name 'activate*'` returns 7, because `.venv/` is both
hidden and ignored; `fd -I` alone still returns 0 and `fd -HI` returns 10. An agent that hits this
once has been taught that `fd` "doesn't find things", which is a durable reason to go back to
`find`. The flags are now named in the rule for that reason. It explains only ~5 of the 37 calls, so
it is a credibility fix rather than the cause.]

[PITFALL: **10 of the 35 avoidable calls — 29% — are `find ~/plans …`, and none of them route to
`fd` at all.** They route to `plans.py`: `list` answers "what plans exist", `archive --search`
answers "which plan said this", and the `plan-docs` skill says outright to use them rather than
opening plan files. So nearly a third of this rule's apparent miss rate is a different skill's
adherence problem wearing `find`'s clothes, and any re-measurement that treats the whole 35 as an
`fd` question will misread the effect of the reword.]

[PITFALL: **the counter over-reports by 10%, the second instance of one bug.** 4 of the 41 tagged
calls are not `find` invocations: three are `audit.py … | rg 'find-not-fd|grep-r-not-rg|…'` — a
session grepping the audit's own output for these very row names — and one is a commit message. The
`rg-replace` row was found to have the identical defect the same day, from prose quoting `rg -rn`.
Both anchor the command name anywhere in the string rather than at a command-segment boundary, so
**every one of these rows inflates precisely when someone is working on the audit**. Filed against
the skill as `2026-09-05-rg-replace-counter-matches-its-own-prose.md`, now covering both. A related
miss in the other direction: the `-printf` call above was tagged `find-not-fd` rather than
`find-exempt`, so the exempt row undercounts too.]

## The pricing lever: looks pulled, mostly is not — 2026-09-05

**`find` has rendered as `ask` since 2026-08-09**, three weeks before this plan proposed pricing it
as the untried strong lever. `cli-allowlist/rules/find.json` classifies it `dangerous` —
`"Includes irreversible operations (-delete) and can execute arbitrary commands via -exec"` — while
`fd`, `rg` and `grep` are `read_only` and render as `allow`. The premise in "Two candidate causes"
above was therefore wrong on the day it was written, and it was **repeated in this session** before
anyone checked `~/.claude/settings.json`.

[DECISION: **step 3 is void as written — but not for the reason first given here, and the first
reason was wrong.** This section originally concluded that the pricing experiment had already run
for three weeks and come back negative: 37 `find` calls a week each paid for with a prompt. That
required the `ask` rule to be what decided, and it mostly was not. **43 of 46 `find` calls in the
week ran under auto mode**, where a classifier decides rather than the allow/ask table; the rule
governed at most the 3 that did not. Pricing is therefore closer to untried than to spent — untried
_in the mode this machine actually runs_. The full correction, and the 96%-auto measurement behind
it, is in `plans/2026-09-05-grep-glob-preference-is-inoperative.md`.]

[PITFALL: **two wrong conclusions in one afternoon, from the same missing fact, and each looked
sound on its own evidence.** First: "there is no price difference" (the plan's, 2026-08-29) —
refuted by reading `settings.json`, where `find` is `ask`. Second: "so pricing already ran and
failed" (this session) — refuted by reading `permissionMode`, which says the table barely applies.
Both readings were correct about the artefact in front of them and wrong about which artefact
governed. The lesson worth keeping is narrow and checkable: **on this machine, a claim about
permission behaviour is not established by reading `settings.json`; it needs the mode the calls
actually ran in.**]

[PITFALL: **the "an ask rule is friction, therefore a lever" reasoning is now untested rather than
refuted**, which matters because the `rg -r` plan's fallback mechanism rests on it. This section
briefly claimed `find` was a live counter-example to it. It is not evidence either way: the rule
that would have made it one was not deciding those calls.]

[PITFALL: **an `ask` classification derived from a tool's most dangerous flag prices every use of
it.** `find` is `ask` because of `-delete`/`-exec`, which 2 of 37 calls used; the other 35 were
read-only lookups paying a dangerous-verb prompt. That is the classifier working as designed —
`no_subcommands = true`, so `find` has one node and one tier — but it means the permission layer
cannot express "this tool is cheap unless you reach for these flags", which is exactly the
distinction both this rule and the `rg -r` fallback want.]

## Open questions

[NEEDS CLARIFICATION: whether a flag-level tier is worth building, now that two rules want it. The
allowlist has `global_option_prefixes` for `git -C`-shaped rewriting, so per-flag tiers are not
alien to it — but `find -delete` and `rg -r` would be the first entries where the flag decides the
tier rather than the subcommand, and Claude Code's rules match a literal prefix, so `Bash(find:*)`
as `allow` plus `Bash(find * -delete:*)` as `ask` does not work: the flag is not a prefix. The
honest options are a coarse tier per tool, or a `PreToolUse` hook this corpus has already rejected
twice.]

Answered by the 2026-09-05 measurement and the reword it produced, kept here because the reasoning
is what the next reading is judged against:

- **Reword, price, or both, and in which order** — reword first and alone, as the plan already
  argued; done 2026-09-05 with no accompanying allowlist change, so the next reading attributes to
  one cause.
- **Should the exemption list stay** — no, not in list form. See the `[DECISION:]` above: it covered
  2 of 37 calls, and is now a bar carrying its own hit rate rather than a carve-out sitting next to
  a preference.

## Recommended direction

Rough, and deliberately sequenced so the result is measurable. Steps 1 and 2 are **done**, on
2026-08-29 and 2026-09-05 respectively; 3 is the live one.

1. ~~**Nothing here is actionable without the audit change**~~ — landed. `session-bash-audit` now
   carries `grep-r-not-rg`, `find-not-fd` and `find-exempt` as separate rows, so the table above is
   the first machine-read figure and the next one is comparable to it rather than to a hand-count.
2. ~~**Reword the clause first, alone.**~~ — landed 2026-09-05, and deliberately alone: no allowlist
   change accompanies it, so the next reading attributes cleanly. `fd` has its own sentence in
   translation form, the exemption list became a bar carrying its own hit rate, and the `-H`/`-I`
   silent-zero caveat is stated.
3. **The allowlist step needs restating, not executing.** `find` has rendered as `ask` since
   2026-08-09, so the lever looks pulled — but 43 of the week's 46 `find` calls ran under auto mode,
   where a classifier decides and the allow/ask table mostly does not. Pricing is untried in the
   mode that runs, and "price it" is not a well-formed step until that is settled. What remains is
   to re-measure the reword after a week with `audit.py --days 7`, correcting for the 10% prose
   over-report until the counter is fixed, and to **read the `~/plans` cluster out separately**: 29%
   of the misses are a `plan-docs` adherence problem that no wording of this rule can move. If the
   reword also fails, both available levers are spent for this clause and the open question above —
   a flag-level tier — is what is left.
4. **Leave `rg` alone.** At 94.5% it is evidence the rule shape works when the preference is stated
   plainly, which is the argument step 2 acted on.

[UNVERIFIED: whether the reword moves it. Two consecutive readings a week apart under an unchanged
rule gave 57% and 60%, so the baseline is stable enough that a real change should be visible. If the
next reading is inside that band, teaching is spent for this clause and step 3 is owed — which is
the same crossroads the `head`/`tail` cluster reached after four attempts, arrived at here after
one.]

[DEFERRED: the general finding, which outlives this rule — a preference clause with an adjacent
exemption list adheres worse than one without. Two spellings of the same preference in one file, one
with carve-outs and one without, measured 92% and 57%, and re-measured 2026-09-05 at 94.5% and 60%.
**The second reading is not a second instance** — it is the same pair a week later, so it says the
observation is stable, not that it generalises. What it did buy is a stronger version of the
hypothesis: the carve-out covers 2 of 37 calls, so it cannot be doing much work as an exemption and
is left doing work as a signal. Cutting it is now a deliberate test of the finding rather than only
a fix to this clause, and the reading after it is the evidence to write down or discard.]
