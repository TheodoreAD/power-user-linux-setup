---
status: idea
updated: 2026-09-02
source_repo: github.com-personal/agent-skills
source_session: 630e8ae3-ecce-4a23-90cf-934ab0698945.jsonl
source_moment: 2026-09-02T14:28:19+03:00
---

# Adherence sample: `head/tail` at its worst yet, and `git -C <own repo>` gone to zero

Third sample for the `~/AGENTS.md` adherence watch, filed alongside
`2026-09-02-adherence-sample-a-verbose-gate-and-a-masked-exit.md` and
`2026-09-02-adherence-sample-first-run-under-the-until-rule.md` rather than merged into either —
this one carries a result that speaks directly to the second's open question, which is the reason it
is worth a file.

## The numbers

`audit.py --session 630e8ae3… --until 2026-09-02T14:28:19+03:00 --compare 2026-08-24-auto-mode.json`
over an `agent-skills` session of **157 Bash calls** before the harvest boundary, **9/11
expectations met**:

| tag                     | rate | vs baseline             |
| ----------------------- | ---: | ----------------------- |
| `chain`                 |  57% | −9pp, OK                |
| **`head/tail`**         |  38% | **+8pp, MISS**          |
| **`cat-view`**          |   2% | **+0pp, MISS**          |
| `sed-n`                 |   3% | −5pp, OK                |
| `heredoc`               |   4% | −12pp, OK               |
| `cd-own-repo`           |   1% | −2pp, OK                |
| `git-C-own-repo`        |   0% | +0pp, OK                |
| `git-C-mutating`        |   1% | −2pp, OK                |
| `git-mutating-in-chain` |   6% | −3pp, OK                |
| `exit-masked`           |  27% | (not in `EXPECTATIONS`) |

Both honesty figures, per the `--until` rule: **38% `head/tail` during the work, 36% including the
harvest's own sweep** — so on this run the sweep _lowered_ the rate rather than raising it, the
third direction observed in three samples and further evidence that "the harvest inflates its own
number" is not a claim anyone should make.

## What this sample adds

**`git -C <own repo>` at 0%, on a session with the same shape that produced 23%.** The
first-run-under-`--until` sample recorded 23% as its dominant miss and tagged an `[UNVERIFIED:]`
asking whether that was characteristic of the machine or of that session's shape — "one session
working in a single repo for ten hours is close to the worst case for that pattern". This session is
that same shape: one repo, one working day, 157 calls, never leaving `agent-skills` except for two
read-only lookups. It scored **0%**, with `cd-own-repo` at 1% (two calls, both `cd <own repo> && rg`
chains).

So the 23% was **that session's habit, not the machine's**. Two sessions, same repo shape, same
rules in force, 23pp apart. That does not make the rate uninteresting — it makes it a per-session
disposition, which is a different thing to fix than a wording problem, and it is the answer that
open question asked for.

**`head/tail` at 38% is the highest in the three samples** (24%, then 45% on an `ingesta` session,
now 38%) and it is +8pp against the baseline the rule was written to improve on. 60 of 157 calls.
The session that produced it spent its day writing, among other things, a `session-bash-audit`
`[PITFALL:]` that says to run the audit unpiped in every mode — and then piped 60 of its own calls.
Third confirmed instance of **authoring a rule is not evidence of following it**, and the first
where the rule authored and the rule broken are the same sentence.

**`cat-view` is a `+0pp` MISS at 2%, which is a scoring shape worth knowing about.** The baseline
was also 2%; a "down" expectation treats equal as failure, so an unchanged low rate scores as a miss
indistinguishable in the output from a regression. Not a bug — `after < before` is the right test —
but a 2% MISS and a 38% MISS read identically in the `n/m` line, and only the per-tag cell says
which is which. Read the cells, not the score.

**The `exit-masked` consequence, checked under the rule that landed the same day.** 27% across 157
calls. `session-harvest` step 5 now asks two things rather than one: re-run the gate unpiped, and
count how many times the session _asserted_ a green result on a masked call.

- Re-run: `inv quality.precommit > log 2>&1; echo $?` → `EXIT=0`. The greens were real.
- Count: **3 assertions** to the user — one report line ("`inv quality.precommit` green (260
  passed)") and two `AskUserQuestion` bodies ("Gate green, scan clean", "gate green, tree clean").
  All three from `| tail`-ed runs; all three hold.

That is the rule's first live application, and it behaved as designed: a footnote rather than a
finding, because the re-run agreed. Worth recording that the count was **3 and not fifteen** — the
`ingesta` session that motivated the rule reported green roughly fifteen times over ten hours, so
the count tracks how chatty the session is about its gate, not how bad the piping is. Two sessions
at 27% and 28% `exit-masked` produced 3 and ~15 assertions respectively.

## Fourth sample, 2026-09-02 — 55% on a docs session, and the prose hypothesis holds

A `power-user-linux-setup` session of **350 Bash calls** before its harvest boundary, 7/11
expectations met. It spent its whole day on documentation: a generated package catalog and task
index, four mermaid diagrams, an `ai.md` split, a 38-page opener/see-also sweep.

| tag                         | rate | vs baseline     |
| --------------------------- | ---: | --------------- |
| `chain`                     |  64% | −3pp, OK        |
| **`head/tail`**             |  55% | **+24pp, MISS** |
| **`sed-n`**                 |  10% | **+2pp, MISS**  |
| **`cat-view`**              |   2% | **+0pp, MISS**  |
| **`git-mutating-in-chain`** |  10% | **+1pp, MISS**  |
| `heredoc`                   |   5% | −11pp, OK       |
| `cd-own-repo`               |   1% | −3pp, OK        |
| `git-C-own-repo`            |   0% | +0pp, OK        |
| `exit-masked`               |  32% | (unscored)      |

**This is the answer the open question below asked for, and it is the strongest evidence in the
corpus.** The hypothesis was that `head/tail` is worse in sessions that write prose than in sessions
that write code, from a 24 / 45 / 38 split. This session is the purest prose case yet — nearly every
call either read a file to quote from or ran a gate to confirm markdown formatting — and it is both
the **largest sample (350 calls, more than twice any other)** and the **highest rate (55%, +10pp on
the previous worst)**. Four samples now: 24% code, 45% prose, 38% prose, 55% prose. The one
code-shaped session is the one low rate.

The mechanism is visible in the samples rather than inferred. The dominant shape is
`inv quality.precommit 2>&1 | rg -n 'error|Error|FAIL|passed' | head -4`, run after nearly every
edit — a gate whose output is long, whose answer is one line, and whose exit code the pipe discards.
`sed-n` at 10% is the same instinct aimed at files: 36 calls reading a known line range to quote it,
where `Read` with `offset`/`limit` is the tool. That supports the question's own proposed fix —
`Read` for the first shape, the harness's truncation for the second — over more wording.

**`exit-masked` at 32% is the highest recorded, and its consequence check fired clean again.** Five
assistant messages asserted the gate or the strict docs build was green, every one from a filtered
run; the unpiped re-run (`inv quality.check`, then `uvx zensical==0.0.44 build --strict`) exited 0
for both, so all five hold. Third live application of that rule, third time a footnote. The count
tracks chattiness as this plan already noted: 3, ~15, and now 5.

[PITFALL: the session was not merely piping a noisy gate — it piped the one command whose exit code
was the entire question, and it did so while **writing documentation about that exact hazard**. The
same run added a `CONTRIBUTING.md` warning that a green local `zensical` build does not imply a
green deploy, then verified its own fix with `uvx … build --strict 2>&1 | tail -2`. Authoring the
rule is not evidence of following it, restated a third time in this corpus.]

## Open questions

[NEEDS CLARIFICATION: is `head/tail` measurably worse in sessions that write prose than in sessions
that write code? The three samples split 24% / 45% / 38%, and the two high ones are the two that
spent most of their calls reading files to quote from and running gates to confirm markdown
formatting — both shapes where "I only need the last few lines" feels true. If that holds, the fix
is not more wording: it is that `Read` with `offset`/`limit` is the tool for the first and the
harness's own truncation handles the second, and neither is what the rule currently opens on.]

[NEEDS CLARIFICATION: should `exit-masked` join `EXPECTATIONS`? It is measured, reported and now has
a documented consequence in `session-harvest`, but it is scored by nothing, so a run that halves it
gets no credit and one that doubles it produces no MISS. Against: it is a symptom of `head/tail`
rather than an independent habit, and scoring both double-counts one behaviour.]

## Recommended direction

Nothing to change in `~/AGENTS.md` from this sample. Two of its three findings close questions
rather than opening them — the `git -C` rate is a disposition and not a machine-wide trend, and the
`exit-masked` consequence check works — and the third, `head/tail` at 38%, is the rate the
already-open `2026-08-28-auto-mode-contradicts-bash-rules.md` exists to explain. This is a row for
that plan, not a new argument.
