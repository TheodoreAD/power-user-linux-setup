---
status: idea
updated: 2026-09-08
---

# `~/AGENTS.md` adherence: the sample corpus

Sixteen sessions measured with `session-bash-audit`'s `audit.py`, all taken with
`--until <harvest boundary>` so the harvest's own sweep is excluded from the headline figure. Six
were compared against the `2026-08-24-auto-mode.json` opus-5 baseline (n=1676); **sample 7 was run
without `--compare`**, and so were samples 8, 14 and 15 — they have rates but no baseline deltas.

[PITFALL: **rows 1–11 were measured with an instrument that under-counted. Four have been re-scored;
the other seven are floors, and a floor may only be compared downward.** `audit.py`'s
`strip_heredoc` cut a command at its heredoc marker and dropped every command that followed it,
which in this family means the gate run after a patch heredoc. Corpus-wide the correction is
`head/tail` 25.0% -> 27.8% and `exit-masked` 15.3% -> 17.8%, reaching **+12pp** on heredoc-heavy
sessions. Fixed in `agent-skills` on 2026-09-06 (`2248ec7`) and applied here on 2026-09-07, from the
now-retired `2026-09-06-adherence-corpus-rows-understated-by-the-heredoc-bug.md` — that name is what
`plans.py archive --search` needs to read the decision back. **Rows 6, 7, 8 and 11 carry a `†` and
were re-measured at their own recorded `--until` boundary**, which reproduces each row's published
`calls` figure exactly — that is what makes the new rate a correction of the old one rather than a
different measurement. **Every other row of 1–11 is a floor**: its true rate is at or above what is
printed, by an amount that varies with how many heredocs that session wrote, and the boundary needed
to correct it was never recorded. Rows 12 and 13 were measured after the fix.]

[PITFALL: **a whole-transcript re-score is not a correction, and on one row it reads as an
improvement that never happened.** Sample 1 has no recorded boundary: measured whole it is 384 calls
against the row's 331, and its `exit-masked` comes out **18% against the published 19%** — lower,
after a fix that can only ever raise the count, because the extra 53 calls were cleaner than the
ones in the original window. Sample 8 diverges the same way from the other side: 18% at its recorded
boundary over 220 calls, 15% over the whole 269. Re-scoring a row without its boundary changes the
denominator silently and stops it being comparable with its neighbours, which is the corpus's whole
value.]

[PITFALL: **the baseline moved out of the skill on 2026-09-04, so the command in every row above is
stale.** `session-bash-audit` now expects `--compare ~/.local/state/session-bash-audit/<name>.json`
— a baseline **you** saved with `--save-baseline` — and tells a reader with none saved to skip the
comparison rather than reach for the shipped file, on the grounds that a baseline measured on
somebody else's machine reports how your session differs from their setup. The shipped
`references/baselines/2026-08-24-auto-mode.json` still exists in both the install and the checkout,
and for this corpus it was measured on this machine, so rows 1–6's **baselines** remain valid as
recorded — their rates are the instrument pitfall's business, not this one's. But nothing has been
saved to the XDG path yet, so a new sample either re-uses the shipped file against current guidance
or, like sample 8 below, runs uncompared. Save the existing baseline to
`~/.local/state/session-bash-audit/` before the next sample if the deltas are to stay comparable.

**Done 2026-09-04**: `~/.local/state/session-bash-audit/2026-09-04.json`, 7,580 calls over 25 main
sessions from 2026-09-01..04, all `claude-opus-5`. **Rows 9 and 10 are the first measured against
it**, so their scores are not comparable with rows 1–6's — a different baseline, on a different
window. Its stored note records the one confound worth knowing: at least one session in the window
ran in auto mode, whose system reminder asks for `cat`/`sed -n` over `Read`, so `cat-view`, `sed-n`
and `grep/find` are mode-mixed in it while `chain`, `head/tail` and `exit-masked` are not.]

Merged on 2026-09-02 from five plans filed separately by five sessions, each of which found the
store dirty and added a file rather than editing one another session might have been holding, again
on 2026-09-03 from two more filed the same way from sessions in other repos, and again on 2026-09-08
from three rows in two files:

- `2026-09-02-adherence-sample-first-run-under-the-until-rule.md` (sample 1)
- `2026-09-02-adherence-sample-a-verbose-gate-and-a-masked-exit.md` (sample 2)
- `2026-09-02-adherence-sample-head-tail-high-git-c-gone.md` (samples 3 and 4)
- `2026-09-02-adherence-sample-a-research-session-in-another-repo.md` (sample 5)
- `2026-09-02-adherence-sample-the-session-that-wrote-the-rule.md` (sample 6)
- `2026-09-03-adherence-sample-the-masked-calls-were-the-gate.md` (sample 7)
- `2026-09-05-adherence-sample-sed-n-at-a-record-high.md` (sample 11), merged 2026-09-05
- `2026-09-06-post-heredoc-fix-adherence-row-from-an-announced-session.md` (sample 12), merged
  2026-09-06 — filed from `ingesta` asking to be absorbed here rather than kept as a third plan
- `2026-09-07-adherence-sample-a-rules-authoring-session-that-broke-them.md` (samples 14 and 15),
  filed from `repo-tasks` for a corpus it could not edit, absorbed and merged 2026-09-08
- `2026-09-08-adherence-sample-the-best-row-the-corpus-has-and-it-announced.md` (sample 16), written
  in this repo and deliberately held apart from the corpus so that all three could be merged in one
  pass rather than three edits to the same table

Those names are what `plans.py archive --search` needs to read any of them back.

Each sample carried its own `source_repo`/`source_session`/`source_moment` frontmatter, which one
merged file cannot. Kept here instead, because a triage session re-reading the original turns is the
whole point of recording them — and the harness keeps a transcript for 30 days by default, so rows
1–13 expire around 2026-10-02 and rows 14–16 around 2026-10-06:

| #  | source repo              | transcript                                   | session start               |
| -- | ------------------------ | -------------------------------------------- | --------------------------- |
| 1  | `agent-skills`           | `2312636b-3f89-4cb5-95e8-48f986fb9ecb.jsonl` | `2026-09-01T17:20:53.485Z`  |
| 2  | `ingesta`                | `bf19d40e-bb8f-4341-a396-77194e946991.jsonl` | `2026-09-02T03:05:26+03:00` |
| 3  | `agent-skills`           | `630e8ae3-ecce-4a23-90cf-934ab0698945.jsonl` | `2026-09-02T14:28:19+03:00` |
| 4  | `power-user-linux-setup` | not recorded                                 | 2026-09-02                  |
| 5  | `ingesta`                | `6be217e8…` (short form only)                | 2026-09-02                  |
| 6  | `agent-skills`           | `13aa58df-3551-49b7-ac0e-0c3693bf8221.jsonl` | `2026-09-02T20:32:51+03:00` |
| 7  | `ingesta`                | `7dab6dae-7c67-454f-bba1-981fe3845089.jsonl` | `2026-09-03T13:47:32+03:00` |
| 8  | `power-user-linux-setup` | `92f54986-8a19-49a4-b792-8ebb1d5fcf1a.jsonl` | `2026-09-03T20:45:51.765Z`  |
| 9  | `repo-tasks`             | `1f762304-ee1a-4bfb-a78f-52da747d29e3.jsonl` | `2026-09-04T12:25:24.475Z`  |
| 10 | `power-user-linux-setup` | `bc30285c-145c-494d-b2d1-be6b37cd37f1.jsonl` | `2026-09-04T10:01:32.556Z`  |
| 11 | `ingesta`                | `6291d9d1-b8ed-4826-9967-9ae30f70bebf.jsonl` | `2026-09-05T10:21:37Z`      |
| 12 | `ingesta`                | `88f860c9…` (short form only)                | `2026-09-05T21:03+03:00`    |
| 13 | `power-user-linux-setup` | `3ad94750-3d54-410e-9c1b-9ad44ffc7e14.jsonl` | `2026-09-06T00:41:15.258Z`  |
| 14 | `repo-tasks`             | `52905ee0-50ff-4376-bd19-5ab4d9ca0a24.jsonl` | `2026-09-06T00:11:27.349Z`  |
| 15 | `agent-skills`           | `af52116e-18ca-4557-9fbe-86cec225fe3e.jsonl` | `2026-09-07T12:07:35.439Z`  |
| 16 | `power-user-linux-setup` | `9164dacd-2813-4087-a593-14dc24c44782.jsonl` | `2026-09-07T14:55Z`         |

Row 14's session started on 2026-09-06 and did its working day after a `/clear` on 2026-09-07, which
is why its start and its boundary sit a day apart; row 16's start is recorded to the minute rather
than the millisecond because its filed plan gave a span rather than a timestamp.

Rows 6, 7 and 11 record the filed plan's `source_moment`, which is the **`--until` boundary** rather
than the session start — the two are different ends of the same session, and only the boundary is
needed to reproduce the figures. **Row 8's boundary is recorded in its own section** rather than in
the table above, which is why it is re-scorable and rows 1–5 are not; the re-score decision counted
three such rows because it read only this table, and the fourth turned up while applying it.

**Instrument.** The four `†` rows were re-scored on 2026-09-07 with `agent-skills`'
`skills/session-bash-audit/scripts/audit.py` at **`95f8af7`** — five commits past the
`strip_heredoc` fix, none of which touches the `exit-masked` predicate (checked with `git log -S`),
so the whole of the movement is the heredoc fix. Every other row of 1–11 was measured before
`2248ec7`, and rows 12 and 13 between the two. Recording the commit is what makes the next
instrument change visible instead of silent: without it a rate cannot be told from the rate a later
instrument would have printed for the same session, which is exactly the confusion this plan spent a
week in. `save_baseline` already does this for baselines.

**Rows 14 and 15 do not record their instrument, and the gap was closed by inference rather than by
the row.** Sample 16 records `95f8af7`; the two filed from `repo-tasks` record the boundary and the
shell and not the third thing, on the same day this plan wrote "every future row carries the
instrument commit, the boundary, and the shell". Recovered on 2026-09-08 rather than left open:
`95f8af7` is the newest commit touching `audit.py` and landed 2026-09-07 13:58 +03:00, before both
boundaries, so each row was measured at `95f8af7` or at its parent `43bc1e0` — and `95f8af7` changes
only the expectations/scoring surface, which neither unscored row uses. So the rates are the same
under either, and the pin holds. **That it holds is luck**: an instrument commit that had touched a
counter would have left both rows uncorrectable in exactly the way the un-daggered rows above are.

**The `score` column is deliberately not re-scored, and the re-scored rates do not license one.**
Re-running the comparison today prints 4/12 for sample 6 and 8/12 for sample 11, against the 6/11
and 9/11 recorded — but the expectation set grew by a row and several `zero` expectations changed
from a rate band to a count in `43bc1e0`, so that movement is three instrument changes at once and a
correction of none of them. The rate cells are corrections because the predicate behind them did not
change; the score is a different measurement and is left as the instrument of the day printed it.
The one verdict recorded as changed is sample 11's `chain`, which moves for the heredoc fix alone.

## Context

### The corpus at a glance

| #   | session repo             | calls | shape                          | `head/tail` | `exit-masked` | `git-C-own-repo` | score |
| --- | ------------------------ | ----: | ------------------------------ | ----------: | ------------: | ---------------: | ----- |
| 1   | `agent-skills`           |   331 | code, one repo, ten hours      |         24% |           19% |          **23%** | 9/11  |
| 2   | `ingesta`                |   137 | prose/gate-heavy, ten hours    |         45% |           28% |               0% | —     |
| 3   | `agent-skills`           |   157 | prose, one repo, one day       |         38% |           27% |               0% | 9/11  |
| 4   | `power-user-linux-setup` |   350 | documentation, whole day       |     **55%** |           32% |               0% | 7/11  |
| 5   | `ingesta`                |    84 | domain research + plan writing |         35% |            8% |               0% | 10/11 |
| 6†  | `agent-skills`           |   216 | tooling, the rule itself       |         47% |       **38%** |               0% | 6/11  |
| 7†  | `ingesta`                |   129 | code + plans, fourteen hours   |         38% |           28% |               0% | —     |
| 8†  | `power-user-linux-setup` |   220 | code + docs + vendor research  |         28% |           18% |               0% | —     |
| 9   | `repo-tasks`             |   202 | shared gate, plans, ~12h       |     **15%** |       **10%** |               0% | 10/11 |
| 10  | `power-user-linux-setup` |   355 | docs gate, CI, deps, ~15h      |         23% |           20% |               1% | 8/11  |
| 11† | `ingesta`                |   228 | domain safety rules, one repo  |         27% |           12% |               0% | 9/11  |
| 12  | `ingesta`                |   183 | announced the rule, ~6h        |      **5%** |            8% |               0% | —     |
| 13  | `power-user-linux-setup` |   174 | corporate cert/proxy, ~13h     |         17% |            1% |               0% | 10/13 |
| 14  | `repo-tasks`             |   372 | a detection rule + plans, ~8h  |         42% |           25% |          **19%** | —     |
| 15  | `agent-skills`           |   196 | skills + plans, ~11.5h         |         28% |           23% |               0% | —     |
| 16  | `power-user-linux-setup` |   270 | plans, research, edits, ~6h    |      **2%** |            2% |               0% | 12/13 |

`†` = re-scored 2026-09-07 at the row's own `--until` boundary with the fixed instrument. **Every
un-daggered row of 1–11 is a floor**, so `55%` on row 4 means "at least 55%" and a comparison
against a `†` row only holds in the direction that makes the floor larger. Row 6's `38%` is bolded
as the highest `exit-masked` the corpus can actually assert; row 4's `32%` is a floor that may well
be higher.

Sample 5 is the only one from a project repo rather than a tooling repo, and the only one whose task
was domain research rather than work on the tooling itself. Samples 7, 8, 14 and 15 have no score
because they were run without `--compare`.

**Sample 16 is the best row the corpus has, by a margin no earlier row approaches** — `head/tail` at
2% against a previous best of 5%, `chain` at 7% against a range of 21–64%, `sed-n` and
`git-C-own-repo` at a clean zero, and 12 of 13 expectations met. Sample 9 held the title on the
pre-fix instrument (15%, a floor) and sample 12 took it at 5%; both are now beaten outright by a row
measured with the counting instrument. **Sample 10 is the counterweight**, and is still the more
useful of that pair for what the corpus is actually asking: it is the session that _authored_ the
`| tail` rule change, and it finished at 23%.

**Sample 14 is the other end, and it is the largest row in the corpus** — 372 calls, the highest
`chain` and second-highest `head/tail` recorded, and the second row ever to put `git-C-own-repo` in
double figures. Read against sample 16 from the same week, the spread between the best and worst
rows of this corpus is now 2% against 42% on the same rule, on the same machine, under the same
instructions.

[PITFALL: **sample 10 is the first row measured twice in one session, and the rate got worse between
them.** A harvest at 00:15 read `chain` 45% / `head/tail` 20% / `exit-masked` 22% over 283 calls; a
second at 00:40 read 50% / 23% / 20% over 355. The 72 calls in between were the verification work —
re-breaking an anchor, running the gate against it, checking placements across three repos — and
they are chain-heavier than the session's average, which moved `chain` from OK to a MISS against
baseline. The lesson is not about that session: **a single end-of-session figure is one sample of a
rate that drifts with what the session is doing**, so a row here describes a whole session's mixture
rather than a disposition. Two of the eight rows above were taken at their session's end and none
was taken twice, so nothing in the corpus can currently say how much of the spread is task shape.]

### Sample 1 — `agent-skills`, 331 calls, the first run under `--until`

`audit.py --session … --until <harvest boundary> --compare 2026-08-24-auto-mode.json`, **9/11**:

| tag                  | rate | vs baseline           |
| -------------------- | ---: | --------------------- |
| `chain`              |  34% | −33pp, OK             |
| `head/tail`          |  24% | −6pp, OK              |
| `heredoc`            |   6% | −10pp, OK             |
| `sed-n`              |   2% | −6pp, OK              |
| `cd-own-repo`        |   0% | −3pp, OK              |
| **`git-C-own-repo`** |  23% | **+23pp, MISS**       |
| **`git-C-mutating`** |  16% | **+13pp, MISS**       |
| `exit-masked`        |  19% | (not in EXPECTATIONS) |

**Only 6 calls were excluded by `--until`**, because the boundary is taken at step 0 and this
harvest had barely started — so the figure here is essentially all working session. That is the flag
behaving as intended rather than a null result: the exclusion is small when the harvest is young,
and the point is that it is no longer unknown.

**`git -C <own repo>` at 23% is this session's dominant miss**, and the mechanism is visible in the
transcript rather than inferred: the session worked in one repo all day and reached for
`git -C <that same repo>` as its default shape for every status, log, add and commit. The rule calls
this "the ban on `cd` wearing the recommended flag", and the session never typed `cd` at all —
`cd-own-repo` is 0%. So the habit the rule was written against was fully avoided, and its
replacement scored worse. **Sample 3 answers what this sample could not** — see below; the rate is a
per-session disposition, not a machine-wide trend.

### Sample 2 — `ingesta`, 137 calls, a verbose gate and 28% of exits thrown away

| tag                     |    rate | baseline | verdict         |
| ----------------------- | ------: | -------: | --------------- |
| `chain`                 |     61% |      66% | −5pp, OK        |
| `chain5`                |      9% |      18% | −9pp, OK        |
| **`head/tail`**         | **45%** |      31% | **+14pp, MISS** |
| **`exit-masked`**       | **28%** |      11% | **+17pp, MISS** |
| `heredoc`               |     19% |      16% | +3pp            |
| `cd-own-repo`           |      0% |       3% | −3pp, OK        |
| `git-C-own-repo`        |      0% |        — | OK              |
| `git-mutating-in-chain` |      1% |       8% | −7pp, OK        |

Including the sweep: `head/tail` 42%, `exit-masked` 25% — the sweep **lowered** both.

Both misses come from **one shape, produced 15+ times: `inv quality.precommit 2>&1 | tail -N`.** The
session knew the rule — it is in `~/AGENTS.md`, in context, and this session had read it — and
produced the banned shape anyway, at nearly half of all calls.

[PITFALL: **the flattering explanation was tested and is false.** The hypothesis was that
`inv quality.precommit` emits more than the harness will show, that the harness truncates the middle
and keeps the head, and that the filter therefore buys the one thing being looked for — on which
reading the fix is a `--quiet` mode on the gate. `seq 1 4000` came back complete, all four thousand
lines, no truncation and no elision, so a plain `inv quality.precommit` would have delivered its
verdict, last, in full, every one of those fifteen times. The filter was buying **nothing** — not
even trading the exit code for readability, but discarding it for free. What is left is worse and
simpler: the pipe is a reflex, not a response to anything, typed while reasoning about the next edit
on a command whose output nobody intends to read past the verdict. This plan asserted the
verbose-gate mechanism before checking it, in the same run whose whole subject is a rule being
missed, and was caught only by running the harness check the skill prescribes.]

Two `git push 2>&1 | tail` calls are the same class on an outward-facing command — both pushes did
succeed, confirmed independently by CI.

### Sample 3 — `agent-skills`, 157 calls, `git -C` gone to zero

`--compare 2026-08-24-auto-mode.json`, **9/11**:

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

38% during the work, 36% including the sweep — so here too the sweep _lowered_ the rate.

**`git -C <own repo>` at 0%, on a session with the same shape that produced sample 1's 23%.** One
repo, one working day, 157 calls, never leaving `agent-skills` except for two read-only lookups,
with `cd-own-repo` at 1% (two calls, both `cd <own repo> && rg` chains). So the 23% was **that
session's habit, not the machine's** — two sessions, same repo shape, same rules in force, 23pp
apart. That does not make the rate uninteresting; it makes it a per-session disposition, which is a
different thing to fix than a wording problem.

**`cat-view` is a `+0pp` MISS at 2%, which is a scoring shape worth knowing about.** The baseline
was also 2%; a "down" expectation treats equal as failure, so an unchanged low rate scores as a miss
indistinguishable in the output from a regression. Not a bug — `after < before` is the right test —
but a 2% MISS and a 38% MISS read identically in the `n/m` line. Read the cells, not the score.

`head/tail` at 38% was the highest of the first three samples, and the session that produced it
spent its day writing, among other things, a `session-bash-audit` `[PITFALL:]` saying to run the
audit unpiped in every mode — then piped 60 of its own 157 calls.

### Sample 4 — `power-user-linux-setup`, 350 calls, a documentation day

7/11 expectations met. The session spent its whole day on documentation: a generated package catalog
and task index, four mermaid diagrams, an `ai.md` split, a 38-page opener/see-also sweep.

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

This is the **largest sample in the corpus (350 calls, more than twice any other)** and the
**highest `head/tail` rate (55%)**. The dominant shape is
`inv quality.precommit 2>&1 | rg -n 'error|Error|FAIL|passed' | head -4`, run after nearly every
edit — a gate whose output is long, whose answer is one line, and whose exit code the pipe discards.
`sed-n` at 10% is the same instinct aimed at files: 36 calls reading a known line range to quote it,
where `Read` with `offset`/`limit` is the tool.

[PITFALL: the session was not merely piping a noisy gate — it piped the one command whose exit code
was the entire question, and it did so while **writing documentation about that exact hazard**. The
same run added a `CONTRIBUTING.md` warning that a green local `zensical` build does not imply a
green deploy, then verified its own fix with `uvx … build --strict 2>&1 | tail -2`. **Authoring a
rule is not evidence of following it** — four confirmed instances in this corpus (samples 3, 4, 6,
and the separate `rg -r` finding). In sample 3 the rule authored and the rule broken were the same
sentence; in sample 6 the rule was the session's entire deliverable.]

### Sample 5 — `ingesta`, 84 calls, research in a repo the corpus had not sampled

Session `6be217e8`, roughly three and a half hours: reading vendored reference clones, web research
on clinical guidelines, and writing four plan files plus `AGENTS.md` and `contributing/` edits. Ten
commits, no pushes. **10 of 11** expectations met.

| counter                 | this session | baseline | verdict         |
| ----------------------- | -----------: | -------: | --------------- |
| `chain`                 |          37% |      66% | −29pp, OK       |
| **`head/tail`**         |      **35%** |      31% | **+4pp, MISS**  |
| `exit-masked`           |           8% |      11% | OK on the delta |
| `sed-n`                 |           4% |       8% | OK              |
| `cat-view`              |           1% |       2% | OK              |
| `heredoc`               |           0% |      16% | OK              |
| `cd-own-repo`           |           0% |       3% | OK              |
| `git-C-own-repo`        |           0% |       0% | OK              |
| `git-mutating-in-chain` |           0% |       8% | OK              |

`git-mutating-in-chain` at 0% across ten commits, all made by pathspec in their own calls.

**Including the sweep: `head/tail` 40%, `exit-masked` 12%** — the sweep _raised_ both, the opposite
direction from samples 2 and 3.

[DECISION: **"the harvest inflates its own number" is not a claim anyone should make.** Three
directions observed across five samples — the sweep lowered the rate twice, raised it once, and
moved it barely at all when the harvest was young. The sweep's effect is a property of the run, not
a bias with a sign, which is why `--until` reports both figures rather than correcting one.]

**`head/tail` (29 calls) splits into two populations that deserve different treatment.** Roughly
half are `rg … | head -N` over vendored reference clones in `$RESEARCH_HOME` — searching an
unfamiliar third-party codebase, where the honest alternative is `rg -c` first and the session did
not reach for it. The other half are `inv quality.precommit 2>&1 | tail -N`, which is the gate case
and is the one that matters. `exit-masked` (7 calls) is almost entirely that same gate.

### Sample 6 — `agent-skills`, 216 calls, the session that spent the day writing this rule

`--compare 2026-08-24-auto-mode.json`, **6/11** — the lowest score in the corpus. **† re-scored
2026-09-07** at `--until 2026-09-02T20:32:51+03:00`, `audit.py` at `95f8af7`: 216 calls, the same
denominator the row published.

| tag                    |      rate | vs baseline     |
| ---------------------- | --------: | --------------- |
| `chain`                | 50% → 62% | −5pp, OK        |
| **`head/tail`**        | 36% → 47% | **+17pp, MISS** |
| **`heredoc`**          |       17% | **+1pp, MISS**  |
| **`sed-n`**            |       11% | **+3pp, MISS**  |
| **`cat-view`**         |        2% | **+1pp, MISS**  |
| **`git-C-mutating`**   |        2% | **−0pp, MISS**  |
| `cd-own-repo`          |        1% | −3pp, OK        |
| `redirect-then-filter` |        0% | OK              |
| `git-C-own-repo`       |        0% | OK              |
| `exit-masked`          | 27% → 38% | (unscored)      |

Every cell without an arrow was already right: the bug recovered `head/tail`, `exit-masked` and
`chain` calls and left the file-reading rows alone, which is the signature of a fault that hid
commands **after** a heredoc rather than mis-reading the ones it saw. The score does not move — both
changed cells keep the verdict they had.

The with-sweep figure the row published (35% over 226 calls) has not been re-measured and is not
comparable: the transcript now holds 252 calls, so that reading was taken while the harvest was
still running.

**The session's entire subject was this rule.** It shipped `harvest.py` with "nothing runs through a
shell, so no pipe can eat an exit code" as a design principle, wrote the `exit-masked` consequence
rule into `session-harvest`, added `fitness.py derivable` to audit skills for exactly this class of
hand-composed command — and produced `2>&1 | head` in **47%** of its own calls, with 38% masking an
exit code. That is the third independent confirmation of the corpus's sharpest claim: **authoring a
rule is not evidence of following it, and may not even correlate.** Samples 3 and 4 were sessions
that had the rule in context; this one had the rule as its deliverable.

[PITFALL: **the mitigation this row was famous for was an artefact of the bug, and the re-score
kills it.** The row read: "almost every masked call was a read-only listing where the exit code
carried nothing. The repo's gate was run unpiped throughout." The fixed instrument splits the 82
masked calls **30 wrapping a gate, 52 a listing**, and names them in its samples —
`inv quality.precommit 2>&1 | tail -5`, `python3 -m pytest … -q 2>&1 | tail -30`. The gate was not
run unpiped throughout; the calls that piped it were the ones sitting after a patch heredoc, which
is exactly what the instrument dropped. What survives is the outcome rather than the
characterisation: the harvest's own unpiped re-run exited 0, so no green claim in that session was
wrong. **A hand-read "what was masked" is only as good as the call list the reader was shown**, and
this one was read off a list missing 30 of its gate calls.]

That mitigation is what sample 7 was filed to test. Sample 7 remains the sharper row — 31 of its 36
masked calls wrapped a gate — but the re-score makes sample 6 a second instance of the same shape
rather than the opposite pole the corpus recorded it as.

### Sample 7 — `ingesta`, 129 calls, the masked calls _were_ the gate

`audit.py --session 7dab6dae --until 2026-09-03T13:47:32+03:00`, no `--compare`, so verdicts only
where the expectation is absolute. 129 calls before the harvest's own sweep, 142 including it. A
fourteen-hour session: four plan steps built, one plan retired, twelve commits. **† re-scored
2026-09-07** at the same boundary, `audit.py` at `95f8af7`: 129 calls, unchanged.

| tag                         |      rate | verdict |
| --------------------------- | --------: | ------- |
| `chain`                     | 49% → 62% | —       |
| **`head/tail`**             | 32% → 38% | MISS    |
| **`heredoc`**               |       19% | MISS    |
| **`git-mutating-in-chain`** |        8% | MISS    |
| `chain5`                    |        3% | —       |
| **`cat-view`**              |        1% | MISS    |
| **`rg-replace-bundle`**     |   1 (new) | MISS    |
| `sed-n`                     |        0% | OK      |
| `cd-own-repo`               |        0% | OK      |
| `git-C-own-repo`            |        0% | OK      |
| `redirect-then-filter`      |        0% | OK      |
| `exit-masked`               | 22% → 28% | —       |

`rg-replace-bundle` is not a re-score but a row the instrument did not have on 2026-09-03: one
`rg -ril`, surfaced retroactively. Sample 11 carries one `rg -rn` on the same basis. Neither is new
to `plans/2026-09-02-rg-replace-flag-used-twice-in-one-session.md`'s week-wide count, but they are
the first corpus rows to carry the row at all — and both sessions typed the bundle **exactly once**,
which is the case that plan says has no detection signature of its own, since the only thing that
caught it elsewhere was having already done it in the same session.

**Sample 6's mitigation does not apply here, and that is the finding.** This session masked **the
gate itself**: `inv quality.precommit 2>&1 | tail -N` was the house shape for the whole run, along
with every `pytest … 2>&1 | tail -N`. The masked set is not listings with no possible victim; it is
the exact command whose exit code decides whether the work is sound. The re-score puts a number on
what was read by hand here: **31 of the 36 masked calls wrapped a gate**, the most lopsided split in
the corpus — and it strengthens rather than moves the row, since the mitigation it was filed against
turned out not to hold for sample 6 either.

**Seven green claims were made to the user on that evidence**, counted by `harvest.py claims`:

| when              | what was said                                   |
| ----------------- | ----------------------------------------------- |
| 2026-09-02T21:13Z | "Gate green (712 passed)"                       |
| 2026-09-02T21:45Z | "Gate green (712 passed, 1 skipped)"            |
| 2026-09-02T22:04Z | "Gate green (742 passed, 1 skipped)"            |
| 2026-09-03T07:16Z | "Gate green (761 passed, 1 skipped)"            |
| 2026-09-03T09:53Z | "Gate green (821 passed, 1 skipped)"            |
| 2026-09-03T10:15Z | "Gate green (821 passed)"                       |
| 2026-09-03T10:47Z | "Gate green throughout (821 passed, 1 skipped)" |

**The harvest's unpiped re-run exited 0, so all seven hold.** Nothing was published wrongly and
nothing needs correcting. That benign outcome is the reason this row is worth recording rather than
a reason to skip it — see the gate-versus-listing question below, which these two samples together
are what makes answerable.

Its `head/tail` half is unmitigated and adds nothing new: 38% re-scored, against a rule that is
unambiguous and was in context the whole time — mid-band rather than the low end the row was
recorded at.

### Sample 8 — `power-user-linux-setup`, 220 calls, the first mixed masked set

`audit.py --session 92f54986 --until 2026-09-04T11:57:51+03:00`, **no `--compare`** (see the
baseline PITFALL above), so rates without deltas or a score. 220 calls before the harvest's own
sweep, 228 including it. Roughly sixteen hours: a plan corpus merge, a vendor-source survey across
four agents' repos, a deploy-mechanism change with tests, and a home-directory migration.

**† re-scored 2026-09-07** at the same boundary, `audit.py` at `95f8af7`: 220 calls, unchanged.

| tag                     |      rate | note                            |
| ----------------------- | --------: | ------------------------------- |
| `chain`                 | 34% → 35% | lowest in the corpus            |
| **`head/tail`**         | 27% → 28% | MISS                            |
| `exit-masked`           | 17% → 18% | 16 wrapped a gate, 23 a listing |
| `heredoc`               |        8% |                                 |
| `git-mutating-in-chain` |        1% | 3 calls, all `git add && scan`  |
| `cd-own-repo`           |        1% | 2 calls, both cross-repo chains |
| `sed-n`                 |        0% | 1 call                          |
| `cat-view`              |        0% |                                 |
| `git-C-own-repo`        |        0% |                                 |
| `redirect-then-filter`  |        0% |                                 |

**This row barely moved, and that is what the other three are measured against.** +1pp on both
counters, against +11pp on sample 6 — the difference is heredoc density (8% here, 17% there), which
is the mechanism stated as a prediction and then confirmed rather than asserted. A row's correction
is not a constant, and a floor row with few heredocs is nearly right as printed while a
heredoc-heavy one is not.

**This is the corpus's first row where the masked set is genuinely both**, which is what makes it
worth recording at an unremarkable rate — and the re-score is the only place a hand reading and the
instrument can be compared, because this row recorded both. The hand reading said "both" and the
split says **16 gate, 23 listing**: `inv quality.precommit 2>&1 | tail -N` several times **and** a
long tail of `gh api … | head -N` calls from the vendor-source survey. Sample 6's hand reading, on
the same method, was wrong — the difference is that this session's gate calls were not hiding behind
heredocs, so the reader could see them.

**Ten green claims, and the unpiped re-run exits 0 (551 passed), so all ten hold.** The count is the
second-highest in the corpus after sample 2's ~15, on a middling rate — which is the corpus's own
point restated: the headline number does not predict how much is riding on it.

[PITFALL: **the one `sed -n` call is the most interesting cell, because it rounds to 0% and is a
straight rule violation.** `sed -n '136,240p'` was used to read a block of `tasks/tools.py` before
moving it, where `Read` with `offset`/`limit` is the tool and the session had been using `Read`
correctly all day. A single call cannot move a rate, so nothing in the scored output distinguishes
"never did this" from "did it once, deliberately, having reasoned about it" — and this instance was
the latter. Read the samples, not only the rates, is the same lesson sample 3's `+0pp` MISS taught
from the opposite direction.]

### Sample 11 — `ingesta`, 228 calls, `sed -n` at a record high with no auto mode to blame

`audit.py --session 6291d9d1 --until 2026-09-05T10:21:37Z --compare 2026-09-04.json`, **9/11**. 228
calls in the window, 236 including the harvest's own sweep. The session's subject was safety rules
in a medical repository — not tooling work, and not a session with any reason to be careless.

**† re-scored 2026-09-07** at the same boundary, `audit.py` at `95f8af7`: 228 calls, unchanged.

| tag                         |      rate | vs baseline                    |
| --------------------------- | --------: | ------------------------------ |
| **`chain`**                 | 39% → 50% | **+5pp, MISS** (was −7pp, OK)  |
| `chain5`                    |        2% | —                              |
| `head/tail`                 | 24% → 27% | −4pp, OK                       |
| **`sed-n`**                 |       16% | **+11pp, MISS**                |
| `heredoc`                   |       11% | −2pp, OK                       |
| `exit-masked`               |  7% → 12% | 25 wrapped a gate, 3 a listing |
| **`git-mutating-in-chain`** |        7% | **+1pp, MISS**                 |
| **`rg-replace-bundle`**     |   1 (new) | MISS                           |
| `cat-view`                  |        1% | −0pp, OK                       |
| `cd-own-repo`               |        0% | −1pp, OK                       |
| `git-C-own-repo`            |        0% | −2pp, OK                       |
| `redirect-then-filter`      |        0% | −0pp, OK                       |

**This is the only cell in the corpus where the fix flips a verdict**: `chain` was recorded as a
7-point improvement on baseline and is a 5-point regression, because a chained command sitting after
a heredoc is a chained command the instrument never saw. A row's `head/tail` moving is a number; a
row's `chain` moving turns "this session was better than the machine" into its opposite.

**16% is the highest `sed-n` the corpus has recorded**, against previous rows of 0%, 2%, 3%, 4%, 8%,
10% and 11% — and this is the row that removes the standing explanation for the two high ones.
Samples 4 and 6 sat at 10% and 11% under auto mode, whose system reminder asks for `cat`/`sed -n`
over the dedicated tools; **this session was in the default mode**, had no competing instruction,
and went higher than either. So the behaviour is not auto-mode compliance leaking into the numbers.

The calls are uniformly **reading a known line range of a source file to quote it into the
conversation** — `sed -n '331,360p' src/ingesta/store/tables.py`, `sed -n '240,285p'` of a TOML
catalogue — never a filter in a pipeline, never a case `Read` with `offset`/`limit` could not serve.
That is the same characterisation sample 4's 10% row gives, so the shape is stable across samples
and only the rate moved. Pair it with `head/tail` at 27% (61 calls, mostly `| head -20` on `rg`):
the two are one instinct aimed at files and at output respectively, and both are the global rule's
"prefer the dedicated harness tool" losing to shell idiom under time pressure.

**Nine green claims, and the unpiped re-run exits 0 (1020 passed), so all nine hold.** Every one of
those greens came from a run piped through `rg` or `tail` — `inv quality.precommit 2>&1 | tail -40`
and several `pytest -q 2>&1 | rg "passed|failed"`. The re-scored split agrees with that reading and
sharpens it: **25 of the 28 masked calls wrapped a gate**, so at 12% this is the corpus's purest
gate-masking row — a low rate carrying almost nothing but the calls that matter.

[PITFALL: **the session that produced these numbers had the rule in front of it all day.** It spent
the day writing safety rules into a medical repository — about not inventing figures, about stating
a bound with every total — and broke the `sed -n` rule in sixteen per cent of its calls while doing
it. That is the same shape as the corpus's authoring-a-rule note above, arriving from a fifth
independent direction, and it is the argument for measuring rather than asking whether a rule is
understood.]

### Sample 12 — `ingesta`, 183 calls, the first row measured after the heredoc fix

Session `88f860c9`, 2026-09-05 21:03 to 2026-09-06 03:12, about six hours, 183 calls before the
harvest's own sweep. No `--compare`, so rates without a score. **Measured with the fixed
`strip_heredoc`** (from the `agent-skills` checkout, `2248ec7` and siblings, unpushed at the time),
which is what makes it incomparable with the rows above until they are re-scored.

| tag                     | rate           |
| ----------------------- | -------------- |
| `chain`                 | 21%            |
| `sed-n`                 | 11% (21 calls) |
| `exit-masked`           | 8% (15 calls)  |
| `head/tail`             | 5% (10 calls)  |
| `cat-view`              | 4% (8 calls)   |
| `chain5`                | 2% (3 calls)   |
| `heredoc`               | 0%             |
| `cd-own-repo`           | 0%             |
| `git-C-own-repo`        | 0%             |
| `git-mutating-in-chain` | 0%             |

**`head/tail` at 5% is the corpus low by a wide margin** — the previous best was sample 9's 15%,
against a band of 24–55% everywhere else — and it was measured by the instrument that counts _more_,
not less. Whatever produced it, it is not a measurement artefact in the flattering direction.

**The session announced the resolution in its first message**, in the phrase
`2026-08-28-auto-mode-contradicts-bash-rules.md` already tracks: _"Using Read/Edit/Write for files
despite the auto-mode note, and `rg` for search — per `~/AGENTS.md`."_ It then read files through
`sed -n` twenty-one times and `cat`/`head` eight more — 29 Bash file views against the rule it had
just said out loud it was following, while the truncation rules it did not announce came out at the
corpus's best figures. That is a fourth instance of announcement-as-substitute, from a fifth
session, and the row is recorded there too.

[PITFALL: **the two zero rows worth a second look are `git-C-own-repo` and `cd-own-repo`, and here
they are genuine.** A zero from an instrument is a claim to check rather than a result to report:
this session used `git -C` seven times and every one targeted `~/plans` or `agent-skills`, which are
genuinely other repos, and it never `cd`-ed at all. A `git-C-own-repo` of 0% in a session that used
`git -C` at all is exactly the shape that deserves the check.]

### Sample 13 — `power-user-linux-setup`, 174 calls, the lowest `exit-masked` the corpus has

`audit.py --session 3ad94750 --until <harvest boundary> --compare 2026-09-06-zero-on-count.json`,
**10/13**. A thirteen-hour session: three corporate cert/proxy features, seventeen commits, five
plan files touched.

| tag                       | rate | vs baseline       |
| ------------------------- | ---: | ----------------- |
| `chain`                   |  35% | −12pp, OK         |
| **`head/tail`**           |  17% | −11pp, OK         |
| `search\|head`            |  15% | —                 |
| `git-mutating-in-chain`   |   5% | −1pp, OK          |
| **`echo-exit`**           |    7 | **MISS**          |
| **`rg-replace-bundle`**   |    2 | **MISS**          |
| `chain5`                  |   4% | —                 |
| **`cd-own-repo`**         |    1 | **MISS**          |
| `exit-masked`             |   1% | 0 gate, 2 listing |
| `heredoc`, `cat-view`     |   1% | −10pp / −0pp, OK  |
| `sed-n`, `git-C-own-repo` |   0% | OK                |

**`exit-masked` at 1% is the corpus low, and the gate/listing split is why it needs no re-run.**
Both masked calls were listings (`which px && px --version | head -3`, a `python -c` parse probe);
the gate was run plain every time, so the session's three green claims rest on real exit codes. That
is the first row in this corpus where the split answered the question outright rather than by
re-running the gate — worth recording because the previous nine rows all had to. Four of those nine
carry it now, retroactively, out of the re-score: rows 6, 7, 8 and 11. It is derivable from any
transcript the harness still holds, which is what makes the hand-recorded `what was masked` column
obsolete rather than merely tedious — and sample 6 is the proof, since the hand reading and the
derived split disagree there.

**`sed-n` at 0% against sample 11's record 16%**, on a session of comparable length in the same
week. Whatever produces that rate, it is not constant across sessions or repos.

**The three misses are all rules with no ambiguity and no competing instruction**, which is the
corpus's recurring shape rather than a new finding: `echo "exit=$?"` appended seven times to
commands whose exit code the harness already reports; the `rg -r` bundle twice (recorded in
`plans/2026-09-02-rg-replace-flag-used-twice-in-one-session.md`, where it is the first sample after
that rule's rewording); and one `cd <own repo> && …`. None of them was under auto mode, and the
session was in the repo that _owns_ these rules — the fourth instance of authoring-and-breaking.

### Sample 14 — `repo-tasks`, 372 calls, the largest row and the worst chain

`audit.py --session 52905ee0 --until 2026-09-07T19:12:55+03:00`, **no `--compare`**, so rates
without deltas or a score. 372 calls in the window, which passes sample 4's 350 as the largest
sample in the corpus. The session started 2026-09-06 and did its eight working hours after a
`/clear` on 2026-09-07; its subject was writing deterministic detection for a coupling rule.

| tag                                           | rate | note                                     |
| --------------------------------------------- | ---: | ---------------------------------------- |
| **`chain`**                                   |  56% | 210 calls, second only to sample 4's 64% |
| **`head/tail`**                               |  42% | second-highest recorded                  |
| **`exit-masked`**                             |  25% | 93 calls, **74 of them wrapping a gate** |
| **`git-C-own-repo`**                          |  19% | 71 calls, **55 of them mutating**        |
| `search\|head`                                |  19% | 72 calls                                 |
| `heredoc`                                     |  13% | 49 calls                                 |
| `chain5`                                      |   5% | 18 calls                                 |
| `git-mutating-in-chain`                       |    — | 20 calls                                 |
| `sed-n`, `cat-view`                           |   1% | 5 calls each                             |
| `cd-own-repo`, `grep-r-not-rg`, `find-not-fd` |   0% |                                          |

**74 of 93 masked calls wrapped a gate — the largest masked-gate population the corpus holds**, and
the first time the derived split has answered the question on a _high_ rate rather than a low one.
`setopt` answered `pipefail` in this session's own shell, so the seven green-gate claims stood on
real exit codes and no re-run was owed. Sample 13 was the first row where the split replaced a gate
re-run; this is the first where it replaced a re-run that 74 calls were riding on.

**`git-C-own-repo` at 19% with `cd-own-repo` at 0%** is sample 1's exact shape arriving a second
time, and the more lopsided of the two: 55 of the 71 were mutating, against sample 1's 16%. The
rule's own claim — that the recommended flag is now the commoner mistake than the banned `cd` it
replaced — has been observed twice with the `cd` at a clean zero both times.

**`chain` at 56% is one habit repeated, not 210 decisions.** The shape is
`git add <paths> && plans.py scan --mode staged` before every commit, plus
`inv quality.precommit 2>&1 | tail -N && git add …`. The filed plan read the first of those as two
rules meeting at one point and asked the corpus to decide it; see the open question below, where it
does not survive inspection.

**The session's subject was a detection rule, and it broke four Bash rules writing it** — the
corpus's recurring shape, now at the highest rates it has produced.

### Sample 15 — `agent-skills`, 196 calls, the same seam in a different repo

`audit.py --session af52116e --until 2026-09-07T23:43:57+03:00`, no `--compare`, from the same filed
plan and added to it 2026-09-07. 196 calls over ~11.5 hours, 8 sweep calls excluded.

| tag                     |   rate | note                               |
| ----------------------- | -----: | ---------------------------------- |
| **`chain`**             |    57% | 112 calls                          |
| `head/tail`             |    28% |                                    |
| `exit-masked`           |    23% | `pipefail` in force, 5 gate claims |
| `chain5`                |    11% | 21 calls                           |
| `git-mutating-in-chain` |      — | 12 calls                           |
| `heredoc`               |     6% | 11 calls                           |
| `search\|head`          |     5% | 10 calls                           |
| `sed-n`, `cat-view`     |     1% | 2 and 1 call                       |
| `find-not-fd`           |     1% |                                    |
| `cd-own-repo`           | 1 call |                                    |
| `git-C-own-repo`        |     0% | `git-C-mutating` 1                 |

**The chain seam reproduces**: 57% here against 56% in sample 14, different repo, different subject,
dominated by the same `git add <paths> && plans.py scan --mode staged`. Two rows are what turn one
session's observation into something worth deciding.

**And one finding that is not a rate.** `~/AGENTS.md` names the exact command, the exact failure and
the mechanism: `gh run list --commit <7-char-sha>` prints `[]` and exits 0 because `--commit`
matches only the full 40-character SHA, so an `until` loop over it can never become true and "still
running" is indistinguishable from "will never finish". This session reproduced it **verbatim** —
short SHA, `until` loop, the wait moved to the background at its timeout — with the rule sitting in
its context. Recovery cost one `git rev-parse HEAD`, which is what makes it easy to under-weight.

[PITFALL: **this is the corpus's sharpest instance of its own claim, and it moves the claim one step
further along.** Every earlier instance was a session that had _authored_ the rule it broke —
samples 3, 4, 6, 11, 13. Here the rule was authored elsewhere, and what the session had was the
finished text: the command named, the failure named, the mechanism explained, the working
replacement given. It typed the failing form anyway. So "authoring a rule is not evidence of
following it" understates the problem — **reading one is not evidence either**, and the corpus has
no sample that separates "had not read it" from "had read it and did it regardless", because every
session here had it in context the whole time.]

### Sample 16 — `power-user-linux-setup`, 270 calls, the best row the corpus has

`audit.py --session 9164dacd --until <harvest boundary> --compare 2026-09-06-zero-on-count.json`,
instrument at **`95f8af7`**, **12/13**. About six hours, 2026-09-07 14:55Z to 21:15Z, on plan work,
clone-and-grep research and long `Edit` runs.

| tag                     |   rate | vs baseline    |
| ----------------------- | -----: | -------------- |
| `chain`                 |     7% | −40pp, OK      |
| `head/tail`             | **2%** | −27pp, OK      |
| `exit-masked`           |     2% | 2 gate, 3 list |
| `search\|head`          |     1% | —              |
| `heredoc`               |     1% | −10pp, OK      |
| `cat-view`              |     0% | −1pp, OK       |
| **`rg-replace-bundle`** |  **1** | **MISS**       |
| `sed-n`                 |     0% | −5pp, OK       |
| `cd-own-repo`           |     0% | OK             |
| `git-C-own-repo`        |     0% | OK             |
| `git-mutating-in-chain` |     0% | −6pp, OK       |

**Four headline counters are corpus bests and nothing else is mid-band.** `head/tail` at 2% against
a previous low of 5% and a band of 15–55% everywhere else; `chain` at 7% against 21–64%; `sed-n` and
`git-C-own-repo` at zero. `exit-masked` at 2% is second to sample 13's 1%, and its split says 2 of
the 5 masked calls wrapped a gate — with `PIPE_FAIL` in force in this session's shell, so those
greens stood on real exit codes and no re-run was owed.

**This is an announcing session, and it is the row `2026-08-28-auto-mode-contradicts-bash-rules.md`
had been waiting for.** It opened by stating the resolution out loud — _"Using Read/Edit/Write for
files and `rg` for search despite the auto-mode note — per `~/AGENTS.md`"_ — the fifth announcing
row in that plan's table, and the one that settles its narrow claim. The four before it scored Bash
file reads at 18%, 15%, 3% and 6%; this one is **0%** — zero `sed -n`, one `cat`-view call in 270.
What it adds beyond that is the first case where the _unopposed_ rules moved too: `chain` at 7% and
`head/tail` at 2% are rules the auto-mode note says nothing about, and every previous announcing row
left them mid-corpus while the announced half improved.

[NEEDS CLARIFICATION: **so is this an announcement effect at all, or a task-shape effect?** Sample
10's pitfall above says a single end-of-session figure is one sample of a rate that drifts with what
the session is doing, and this session was unusually edit-heavy and research-heavy — long `Edit`
runs and clone-and-grep research, both naturally low in chained shell work. A session that spent six
hours on installer debugging would chain more whatever it announced. Separating the two needs a row
that announces _and_ does shell-shaped work, which nothing has yet supplied — and sample 14, the
shell-shaped row from the same week, did not announce.]

**The one miss is the interesting one.** `rg-replace-bundle = 1`: a single `rg -rn --stats -l` in
the first hour, where `-r` ate the `n` and the flags never applied. It was caught by the documented
detection signature within one call — the output shape was wrong for what had been asked — and the
search re-run correctly. That makes it the fourth occurrence recorded against a session holding the
rewritten clause, and it is carried into
`plans/2026-09-02-rg-replace-flag-used-twice-in-one-session.md` where the count lives.

[PITFALL: **the same session broke the `| head`/`| tail` rule twice and the `find`-versus-`fd` rule
zero times, while spending its day enforcing the truncation rule on three subagents and writing a
new `~/AGENTS.md` rule about research method.** Both violations were self-caught and announced in
the conversation, which is why the rate is 2% rather than higher. That is the seventh instance of
authoring-and-breaking — samples 3, 4, 6, 11, 13, 14 and this one, listed rather than counted
because the corpus's earlier "fourth" and "fifth" tallies were each counting a different subset —
and the mildest form of it on record: the author followed the rule 98% of the time and still
produced the shape. **The corpus should stop reading that claim as being about hypocrisy and start
reading it as a measurement of how weak a rule's grip is at its strongest** — 2% is what
near-perfect adherence looks like, and it is not zero.]

**`head/tail` is worse in prose sessions than in code sessions.** Seven samples: 24% code, then 45%,
38%, 55%, 35% and 47% on sessions that spent most of their calls reading files to quote from and
running gates to confirm markdown formatting. The one purely code-shaped session is the one low
rate, and the largest and most purely prose-shaped session is the highest. **The re-score weakens
the middle of this argument without touching its ends**: sample 7, the one mixed shape — code and
plans in the same run — was recorded at 32%, between the two populations, and at 38% it sits inside
the prose band's low end instead. The code/prose gap is between a 24% floor and a 35–55% spread, so
it survives; the mixed row no longer sits neatly in the gap. That points the fix away from wording:
`Read` with `offset`/`limit` is the tool for the quoting half, and the harness's own truncation
handles the gate half — neither is what the rule currently opens on.

[PITFALL: **sample 16 is the counter-example that claim never had, and it should be retired rather
than patched.** A session that spent six hours on plans, research and edits — the prose end of the
spectrum by every description the claim uses — came in at **2%**, below the one purely code-shaped
row the argument rests on. Samples 14 and 15 do not rescue it either: 42% on a mixed code-and-prose
day and 28% on another sit inside the band the claim assigns to prose, but so did every mixed row
before them. What the three new rows show together is that the spread within one week and one
machine (2% to 42%) is wider than the code/prose gap the corpus spent seven rows describing, so task
shape is at best a weak term in whatever produces this rate. The remedy sentence above survives
untouched — it never depended on the split.]

**`sed -n` is not an auto-mode artefact.** The two high rows before sample 11 — 10% and 11% — were
both auto-mode sessions, where the harness's own reminder asks for `cat`/`sed -n` over `Read`, and
that reading was the standing explanation. Sample 11 ran in the default mode with no competing
instruction and reached **16%**, the corpus high. So the same population produces the behaviour with
and without the reminder, and the reminder is at most an aggravator. The shape is identical in every
row that recorded it: reading a known line range to quote it, where `Read` takes `offset` and
`limit`.

**`git -C <own repo>` is a per-session disposition, not a machine-wide trend.** Sample 1's 23% and
sample 3's 0% came from the same repo, the same shape, the same day's rules. Nothing further is owed
on that question — and **sample 14's 19% confirms it rather than reopening it**, being the third
value in the set and the second non-zero, on a day when samples 15 and 16 sat at zero. What sample
14 does add is cost: 55 of its 71 were mutating `git -C` calls against the session's own repo, so
the disposition, when a session has it, is not confined to the read-only verbs the allowlist waves
through.

**The `exit-masked` consequence check works, and has fired clean every time it has been run.**
`session-harvest`'s rule — a non-zero `exit-masked` means the session's own green results are
unverified, so re-run the gate unpiped and count how many times the session asserted a green on a
masked call:

| sample | `exit-masked` | assertions | what was masked         | unpiped re-run            |
| ------ | ------------: | ---------: | ----------------------- | ------------------------- |
| 1      |   19% (floor) |          — | not recorded            | exit 0                    |
| 2      |   28% (floor) |        ~15 | the gate                | exit 0                    |
| 3      |   27% (floor) |          3 | not recorded            | exit 0                    |
| 4      |   32% (floor) |          5 | the gate                | exit 0                    |
| 5      |    8% (floor) |          6 | mostly the gate         | exit 0, 643 passed        |
| 6†     |           38% |          — | **30 gate, 52 listing** | exit 0                    |
| 7†     |           28% |          7 | **31 gate, 5 listing**  | exit 0                    |
| 8†     |           18% |         10 | **16 gate, 23 listing** | exit 0, 551 passed        |
| 11†    |           12% |          9 | **25 gate, 3 listing**  | exit 0, 1020 passed       |
| 12     |            8% |          — | not recorded            | not run; shell unrecorded |
| 13     |            1% |          3 | **0 gate, 2 listing**   | not owed, `pipefail`      |
| 14     |           25% |          7 | **74 gate, 19 listing** | not owed, `pipefail`      |
| 15     |           23% |          5 | not recorded            | not owed, `pipefail`      |
| 16     |            2% |          2 | **2 gate, 3 listing**   | not owed, `pipefail`      |

The bolded splits are derived by the instrument; the rest are hand readings, and rows 1–5 are floors
whose true rate is higher by an unknown amount. **The last column changes meaning at row 13**: rows
1–11 were re-run because nothing else could answer the question, while rows 13–16 confirmed
`pipefail` in the session's own shell with `setopt` and owed no re-run at all. Row 12 is the one gap
— it did neither, so its 8% is the only masked figure in the corpus whose consequence is still
unknown, and its transcript expires around 2026-10-05.

Every green held. **"No harm done" is the wrong lesson**: the claims were true and the method could
not have distinguished them from false ones, and sample 2's session pushed five times on that basis.
The count tracks how chatty a session is about its gate rather than how bad the piping is — 27% and
28% produced 3 and ~15 assertions respectively.

**So `exit-masked` measures a hazard, not a defect rate** — worth stating outright before somebody
reads a high number as evidence that false claims were made. Seven samples carry a claims count and
a re-run, all seven clean, across a printed range of 8% to 32%; four more (13–16) carry a count that
`pipefail` made a re-run unnecessary for, 17 claims between them. The counter says how much of a
session's evidence _could_ have been wrong, and across eleven samples and roughly seventy claims the
corpus has yet to find a case where any of it was. Sample 11 is still the sharpest version — 12%,
nine claims riding on it, and 25 of its 28 masked calls wrapping a gate — though it is no longer the
lowest rate of any claim-making row, because it moved up and sample 5's floor did not.

[PITFALL: **the hazard this column measures largely stopped existing on 2026-09-05, and nothing in
the table says so.** `[packages.claude-code]`'s `zshenv` snippet gives every Bash-tool shell
`PIPE_FAIL` (landed `38f3422`, 2026-09-05), so a pipeline now reports the rightmost non-zero status
and a piped gate no longer hides its failure. Rows 1–11 predate it and their masked exits were
genuinely masked; rows 12 and 13 do not, and reading their `exit-masked` as the same hazard
overstates it. The two are not the same measurement wearing one column name — which is the
instrument-commit problem again, one layer down: **a rate needs the machine it was measured on, not
only the script.** A session's shell snapshot is captured once, so a session that started before the
deploy kept the old behaviour whatever the date says; `setopt | rg pipefail` is the check.]

**The headline rate cannot tell the three consequences apart, and the re-score makes the point
harder rather than softer.** Four rows, four consequences:

- **sample 6†** — 38%, the highest the corpus can assert, and it was recorded as "listings only,
  damage structurally impossible". 30 of its 82 masked calls wrapped a gate;
- **sample 2** — at least 28%, masked gate, and that session **pushed five times** on evidence it
  could not distinguish from false;
- **sample 7†** — 28%, masked gate, seven assertions to the user, re-run clean;
- **sample 14** — 25%, and **74 of its 93 masked calls wrapped a gate**, the largest masked-gate
  population in the corpus — which cost exactly nothing, because `pipefail` was in force and carried
  every one of those exit codes through the pipe.

One number separates none of them, and the fourth is what makes that terminal rather than
inconvenient: the same counter at roughly the same value now spans "structurally harmless", "pushed
five times on it", "seven claims, re-run clean", and "the shell reported truthfully the whole time".
The last of those is not a property of the session at all. What changed is where the error was: the
corpus used to read the highest of the three as the harmless one, and that reading came from a
hand-built `what was masked` column over a call list the instrument had already pruned. `audit.py`
derives the split now, which is the open question below, answered.

**`audit.py`'s `compare` scored absent baseline tags wrongly, and older rows are affected.** A tag
**missing** from the baseline was treated as `0.0`, so a "down" expectation on a pattern added after
the baseline was saved evaluated `0.0 < 0.0` and reported **MISS at a 0% rate**, while other absent
tags collected an equally unearned **OK**. Sample 1 first printed 9/12 for that reason; the honest
figure is 9/11. Fixed in `agent-skills` on 2026-09-02, with `"zero"` expectations still judged (they
are absolute and need no baseline) and only `"down"` ones skipped as `(new)`. **Any adherence figure
quoted from a run whose baseline predates the pattern is affected, in both directions** — re-read
rather than re-trusted if an older sample's score is ever compared against a newer one.

## Open questions

[DECISION: **the "two rules meet at a seam" reading of samples 14 and 15's chain rate does not
survive inspection, and what is left is more interesting than what it replaces.** The filed plan
asked whether `git add <paths> && plans.py scan --mode staged` — the shape behind 56% and 57% in two
repos — is a different finding from a chain of convenience, on the grounds that "stage immediately
before the commit" and "one command per call" pull against each other at that point. They do not.
Staging, scanning and committing are three calls and nothing in either rule asks for fewer:
"immediately before" orders the steps, it does not forbid an intervening call, and the scan is a
read-only check whose output the user never has to approve. The chain buys one round trip.

What makes it worth recording rather than dismissing is **why it survived roughly twenty repetitions
in one session and then reappeared in another**: it has a rationalisation available. A chain typed
for convenience is visible as laziness on the next read; a chain that looks like two rules being
honoured at once reads as care, and nothing in the session's own view contradicts it. That is a
different failure from the `| tail` reflex, which the corpus has repeatedly found to be typed while
thinking about something else. Both produce the same counter.

The residual is one clause, and it is **deliberately not written here** because admitting one is the
user's call: neither the staging rule nor the chaining rule says the scan is its own call, so a
session reconstructing the sequence has to derive that. Same shape as the truncation clause held
open above.]

[NEEDS CLARIFICATION: **the gate may be the fix rather than the discipline.**
`inv quality.precommit` prints ~45 lines on success, of which the informative part is the last four,
and it is the single biggest contributor to `head/tail` and `exit-masked` in samples 2, 4 and 5
independently. Two levers that do not depend on anybody remembering: a quieter default that prints a
summary on success and the whole thing on failure, or a documented
`inv quality.precommit > log 2>&1` shape with a Read of the log — which the global rules already
prefer and which the sessions demonstrably do not reach for. Sample 2's falsification kills the
"output is truncated so the filter buys something" argument for a `--quiet` flag, but not the
readability argument.]

[DECISION: **the `what was masked` column is derived by the instrument now, and the corpus stops
recording it by hand.** Asked here as an open question, filed to `agent-skills` as the repo that
owns `audit.py`, and answered there on 2026-09-06: `exit-masked` prints
`n masked, of which m wrapped a gate` — one line, one regex over a gate name list, and it classifies
about half the masked population corpus-wide. A second rate column was designed and rejected (sample
8 is 99% listings and the 1% is the part that matters, so a rate averages away the call that
counts), and so was listing the masked gate calls (at corpus scale that is 1,389 calls across 55 of
67 sessions, a report section rather than a footnote). The reasoning and the measurements that
killed each alternative are in that skill's `references/research.md`, "One rate over two outcomes".
The assertions half stays where it was: `harvest.py claims` counts them in the harvest report, and
the corpus quotes the count rather than growing a column for it. **What settles this beyond the
design argument is sample 6**: the hand-built column recorded "listings" for a row whose derived
split is 30 gate calls out of 82, because the reader was shown a pruned call list. A column a human
fills in from an instrument's output inherits every defect of that instrument and reports none of
them.]

### The output ceiling, measured 2026-09-02 — and it is size, not lines

Four probes, `claude-opus-5` under auto mode:

| probe                   | bytes   | result        |
| ----------------------- | ------- | ------------- |
| `seq 1 4000` (sample 2) | ~19 KB  | complete      |
| 365 padded lines        | 25.5 KB | complete      |
| 500 padded lines        | 34.2 KB | **truncated** |
| `seq 1 20000`           | 106 KB  | **truncated** |

So the ceiling is **between 25.5 KB and 34.2 KB and is measured in bytes, not lines** — the 20,000
line probe and the 500 line probe were treated the same way. Not bisected further; the band is
enough for every question this corpus was asking, and the exact constant is the harness's to change.

**What truncation does is the part that settles the argument: it keeps the _first_ 2 KB and writes
the whole output to a file it names.** Two consequences, both against the filter:

- For the gate, which is ~3 KB, the filter buys nothing — confirmed twice now, once by sample 2's
  falsification and once by this band.
- For an output that genuinely _is_ oversized, `| tail -N` is the worst available move rather than a
  defensible trade. It discards the exit code to obtain a tail, while the harness has already put
  the complete text — tail included — in a file that a `Read` or `Grep` can reach at full fidelity.
  The reflex is aimed at a truncation that keeps the head, and it responds by throwing away the half
  the harness kept for free.

[DECISION: **there is no legitimate `| head`/`| tail` case left to carve out.** The corpus opened
this question because half of sample 5's piping was exploratory `rg` over unfamiliar vendored source
where the result-set size was genuinely unknown — the strongest candidate for a justified filter.
The ceiling behaviour answers it: an oversized `rg` is saved whole to a file, so the exploratory
case has the same remedy as the gate case. `rg -c` first remains the cheaper first call, not the
only correct one.]

**Whether unfamiliar third-party source is a legitimate `head` case — answered, no**, by the ceiling
measurement above: an oversized `rg` is saved whole to a named file, so the exploratory population
has the same remedy as the gate population. The two still differ in what a session is _doing_ when
it reaches for the filter, which is worth knowing for wording, but they no longer differ in what the
correct call is.

[DECISION: **`exit-masked` stays out of `EXPECTATIONS`, decided in `agent-skills` on 2026-09-06
(`8b095f5`), and the reason is stronger than the double-counting argument this corpus raised.**
Whether a masked exit code cost anything depends on the shell that ran the command — one setting
`pipefail` carries the status through the pipe and nothing was hidden — and a transcript records the
command, not the shell. Any verdict computed from it is a confident number standing on an assumption
about a machine the instrument never saw. A gate-only version of the row fails the same test.
`head/tail` scores the habit instead, from output loss, which holds on every machine; a test in that
repo pins the absence so it reads as a decision rather than an omission. This machine is exactly the
case that motivates it — see the `PIPE_FAIL` pitfall above.]

## Recommended direction

**Nothing to change in `~/AGENTS.md` from these samples.** Two of the corpus's questions are now
closed — the `git -C` rate is a disposition and not a trend, and the `exit-masked` consequence check
works — and `head/tail`, the one persistent miss, is the rate that
`2026-08-28-auto-mode-contradicts-bash-rules.md` exists to explain. These are rows for that plan,
not new arguments.

**Revised 2026-09-02, after the ceiling was measured.** The gate's verbosity is no longer the open
lever it looked like: the filter buys nothing at 3 KB, and above the ceiling the harness keeps the
head and saves the whole output to a file, so the filter is wrong there too. A quieter
`inv quality.precommit` would still be pleasanter to read, but it can no longer be justified as the
fix for this rate — it would be a convenience change, and three sessions reaching the same command
by the same route is evidence about the habit rather than about the gate.

What the ceiling measurement does open is a candidate clause, deliberately **not** written here
because admitting one is the user's call and the leanness pass has just closed a round:
`~/AGENTS.md` tells sessions the harness truncates and saves the full text to a file, and does not
tell them it keeps the **head**. A reader who knows only "it truncates" has no way to see that
`tail` is aimed at the wrong end. One clause on "Viewing, searching, or editing files".

**Unchanged by samples 6 and 7, 2026-09-03.** Neither adds an argument for a wording change — sample
6 is another `head/tail`/`exit-masked` row and sample 7 is the counterweight that turns sample 6's
mitigation into a distinction worth measuring. The single action they generate is a plan filed in
`agent-skills` for the `audit.py` column, per the open question above; nothing here is owed to
`~/AGENTS.md`. (That plan landed: the split ships, and the question above is now a `DECISION`.)

**Revised 2026-09-07, after the re-score. Still nothing owed to `~/AGENTS.md`, and one method
finding that outlives every rate here.** The corrections moved four rows and flipped one verdict,
and no wording argument turns on any of it — `head/tail` was the persistent miss before and is a
larger one now. What the pass actually produced is a rule about the corpus rather than about the
sessions in it: **a measurement is not a number, it is a number plus the instrument, the boundary
and the machine.** Each of the three was missing somewhere here, and each cost something —
`strip_heredoc` understated eleven rows, the missing `--until` boundary makes seven of them
permanently uncorrectable, and `PIPE_FAIL` silently changed what the `exit-masked` column means
partway through the corpus. A row that records all three can be corrected by anyone later; a row
that records none of them can only be re-measured, which is a different row. Every future row
carries the instrument commit, the boundary, and the shell.

**Revised 2026-09-08, after samples 14, 15 and 16. Still nothing owed to `~/AGENTS.md`, and two
candidate clauses now held open rather than one.** The three rows landed in the same week and span
2% to 42% on the same rule, which retires the code-versus-prose reading and leaves the corpus
without a term that explains the spread. Two questions closed: the chain seam is not a seam (above),
and `git-C-own-repo` has a third value that confirms the disposition reading. One question sharpened
past where its current wording can go — sample 15 broke a rule whose text names the command, the
failure, the mechanism _and_ the replacement, which is every lever a sentence has. The held-open
clauses are the truncation one (the harness keeps the **head**) and now the staging one (the scan is
its own call); both are the user's to admit, and neither is argued for by a rate here.

`2026-09-02-rg-replace-flag-used-twice-in-one-session.md` is a separate finding of the same "simply
not followed" kind and is deliberately not merged here — it is one flag with its own proposed
counter, not a session-level rate. Sample 16's single `-rn` is recorded there, as samples 7, 11 and
13's were.
