---
status: idea
updated: 2026-09-04
---

# `~/AGENTS.md` adherence: the sample corpus

Ten sessions measured with `session-bash-audit`'s `audit.py`, all taken with
`--until <harvest boundary>` so the harvest's own sweep is excluded from the headline figure. Six
were compared against the `2026-08-24-auto-mode.json` opus-5 baseline (n=1676); **sample 7 was run
without `--compare`**, and so was sample 8 — both have rates but no baseline deltas.

[PITFALL: **the baseline moved out of the skill on 2026-09-04, so the command in every row above is
stale.** `session-bash-audit` now expects `--compare ~/.local/state/session-bash-audit/<name>.json`
— a baseline **you** saved with `--save-baseline` — and tells a reader with none saved to skip the
comparison rather than reach for the shipped file, on the grounds that a baseline measured on
somebody else's machine reports how your session differs from their setup. The shipped
`references/baselines/2026-08-24-auto-mode.json` still exists in both the install and the checkout,
and for this corpus it was measured on this machine, so rows 1–6 remain valid as recorded. But
nothing has been saved to the XDG path yet, so a new sample either re-uses the shipped file against
current guidance or, like sample 8 below, runs uncompared. Save the existing baseline to
`~/.local/state/session-bash-audit/` before the next sample if the deltas are to stay comparable.

**Done 2026-09-04**: `~/.local/state/session-bash-audit/2026-09-04.json`, 7,580 calls over 25 main
sessions from 2026-09-01..04, all `claude-opus-5`. **Rows 9 and 10 are the first measured against
it**, so their scores are not comparable with rows 1–6's — a different baseline, on a different
window. Its stored note records the one confound worth knowing: at least one session in the window
ran in auto mode, whose system reminder asks for `cat`/`sed -n` over `Read`, so `cat-view`, `sed-n`
and `grep/find` are mode-mixed in it while `chain`, `head/tail` and `exit-masked` are not.]

Merged on 2026-09-02 from five plans filed separately by five sessions, each of which found the
store dirty and added a file rather than editing one another session might have been holding, and
again on 2026-09-03 from two more filed the same way from sessions in other repos:

- `2026-09-02-adherence-sample-first-run-under-the-until-rule.md` (sample 1)
- `2026-09-02-adherence-sample-a-verbose-gate-and-a-masked-exit.md` (sample 2)
- `2026-09-02-adherence-sample-head-tail-high-git-c-gone.md` (samples 3 and 4)
- `2026-09-02-adherence-sample-a-research-session-in-another-repo.md` (sample 5)
- `2026-09-02-adherence-sample-the-session-that-wrote-the-rule.md` (sample 6)
- `2026-09-03-adherence-sample-the-masked-calls-were-the-gate.md` (sample 7)

Those names are what `plans.py archive --search` needs to read any of them back.

Each sample carried its own `source_repo`/`source_session`/`source_moment` frontmatter, which one
merged file cannot. Kept here instead, because a triage session re-reading the original turns is the
whole point of recording them — and the harness keeps a transcript for 30 days by default, so these
expire around 2026-10-02:

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

Rows 6 and 7 record the filed plan's `source_moment`, which is the **`--until` boundary** rather
than the session start — the two are different ends of the same session, and only the boundary is
needed to reproduce the figures.

## Context

### The corpus at a glance

| #  | session repo             | calls | shape                          | `head/tail` | `exit-masked` | `git-C-own-repo` | score |
| -- | ------------------------ | ----: | ------------------------------ | ----------: | ------------: | ---------------: | ----- |
| 1  | `agent-skills`           |   331 | code, one repo, ten hours      |         24% |           19% |          **23%** | 9/11  |
| 2  | `ingesta`                |   137 | prose/gate-heavy, ten hours    |         45% |           28% |               0% | —     |
| 3  | `agent-skills`           |   157 | prose, one repo, one day       |         38% |           27% |               0% | 9/11  |
| 4  | `power-user-linux-setup` |   350 | documentation, whole day       |     **55%** |       **32%** |               0% | 7/11  |
| 5  | `ingesta`                |    84 | domain research + plan writing |         35% |            8% |               0% | 10/11 |
| 6  | `agent-skills`           |   216 | tooling, the rule itself       |         36% |           27% |               0% | 6/11  |
| 7  | `ingesta`                |   129 | code + plans, fourteen hours   |         32% |           22% |               0% | —     |
| 8  | `power-user-linux-setup` |   220 | code + docs + vendor research  |         27% |           17% |               0% | —     |
| 9  | `repo-tasks`             |   202 | shared gate, plans, ~12h       |     **15%** |       **10%** |               0% | 10/11 |
| 10 | `power-user-linux-setup` |   355 | docs gate, CI, deps, ~15h      |         23% |           20% |               1% | 8/11  |

Sample 5 is the only one from a project repo rather than a tooling repo, and the only one whose task
was domain research rather than work on the tooling itself. Samples 7 and 8 have no score because
they were run without `--compare`.

**Sample 9 is the best row the corpus has** — `head/tail` at 15% against a previous best of 24%, on
a twelve-hour gate-heavy day, and the second consecutive clean `chain`. **Sample 10 is the
counterweight, from the same day and the same baseline**, and is the more useful of the pair for
what the corpus is actually asking: it is the session that _authored_ the `| tail` rule change, and
it still finished at 23%.

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

`--compare 2026-08-24-auto-mode.json`, **6/11** — the lowest score in the corpus. 216 calls before
the harvest's own sweep, 226 including it.

| tag                    | rate | vs baseline    |
| ---------------------- | ---: | -------------- |
| `chain`                |  50% | −17pp, OK      |
| **`head/tail`**        |  36% | **+6pp, MISS** |
| **`heredoc`**          |  17% | **+1pp, MISS** |
| **`sed-n`**            |  11% | **+3pp, MISS** |
| **`cat-view`**         |   2% | **+1pp, MISS** |
| **`git-C-mutating`**   |   2% | **−0pp, MISS** |
| `cd-own-repo`          |   1% | −3pp, OK       |
| `redirect-then-filter` |   0% | OK             |
| `git-C-own-repo`       |   0% | OK             |
| `exit-masked`          |  27% | (unscored)     |

36% during the work, 35% including the sweep — the direction that run happened to lean, and the
reason the rule says to report both rather than to claim the sweep inflates anything.

**The session's entire subject was this rule.** It shipped `harvest.py` with "nothing runs through a
shell, so no pipe can eat an exit code" as a design principle, wrote the `exit-masked` consequence
rule into `session-harvest`, added `fitness.py derivable` to audit skills for exactly this class of
hand-composed command — and produced `2>&1 | head` in **36%** of its own calls, with 27% masking an
exit code. That is the third independent confirmation of the corpus's sharpest claim: **authoring a
rule is not evidence of following it, and may not even correlate.** Samples 3 and 4 were sessions
that had the rule in context; this one had the rule as its deliverable.

**The mitigating half, stated so the row is not read as worse than it is:** almost every masked call
was a read-only listing (`plans.py list 2>&1 | head -60`, `--help | head -30`) where the exit code
carried nothing. The repo's gate was run unpiped throughout, and the harvest's own re-run of it
exited 0 — so no green claim in that session stands on filtered evidence. The rate is high; the
damage from it was nil. Both facts belong here, because a corpus of only the alarming half argues
for a rule nobody can follow.

That mitigation is what sample 7 was filed to test, and it does not survive contact with it.

### Sample 7 — `ingesta`, 129 calls, the masked calls _were_ the gate

`audit.py --session 7dab6dae --until 2026-09-03T13:47:32+03:00`, no `--compare`, so verdicts only
where the expectation is absolute. 129 calls before the harvest's own sweep, 142 including it. A
fourteen-hour session: four plan steps built, one plan retired, twelve commits.

| tag                         | rate | verdict |
| --------------------------- | ---: | ------- |
| `chain`                     |  49% | —       |
| **`head/tail`**             |  32% | MISS    |
| **`heredoc`**               |  19% | MISS    |
| **`git-mutating-in-chain`** |   8% | MISS    |
| `chain5`                    |   3% | —       |
| **`cat-view`**              |   1% | MISS    |
| `sed-n`                     |   0% | OK      |
| `cd-own-repo`               |   0% | OK      |
| `git-C-own-repo`            |   0% | OK      |
| `redirect-then-filter`      |   0% | OK      |
| `exit-masked`               |  22% | —       |

**Sample 6's mitigation does not apply here, and that is the finding.** This session masked **the
gate itself**: `inv quality.precommit 2>&1 | tail -N` was the house shape for the whole run, along
with every `pytest … 2>&1 | tail -N`. The masked set is not listings with no possible victim; it is
the exact command whose exit code decides whether the work is sound.

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

Its `head/tail` half is unmitigated and adds nothing new: 32%, against a rule that is unambiguous
and was in context the whole time, one more point at the low end of the 24–55% band.

### Sample 8 — `power-user-linux-setup`, 220 calls, the first mixed masked set

`audit.py --session 92f54986 --until 2026-09-04T11:57:51+03:00`, **no `--compare`** (see the
baseline PITFALL above), so rates without deltas or a score. 220 calls before the harvest's own
sweep, 228 including it. Roughly sixteen hours: a plan corpus merge, a vendor-source survey across
four agents' repos, a deploy-mechanism change with tests, and a home-directory migration.

| tag                     | rate | note                            |
| ----------------------- | ---: | ------------------------------- |
| `chain`                 |  34% | lowest in the corpus            |
| **`head/tail`**         |  27% | MISS                            |
| `exit-masked`           |  17% | lowest of the high-rate rows    |
| `heredoc`               |   8% |                                 |
| `git-mutating-in-chain` |   1% | 3 calls, all `git add && scan`  |
| `cd-own-repo`           |   1% | 2 calls, both cross-repo chains |
| `sed-n`                 |   0% | 1 call                          |
| `cat-view`              |   0% |                                 |
| `git-C-own-repo`        |   0% |                                 |
| `redirect-then-filter`  |   0% |                                 |

**This is the corpus's first row where the masked set is genuinely both**, which is what makes it
worth recording at an unremarkable rate. Sample 6 masked only listings and sample 2, 4 and 7 masked
the gate; this session did both — `inv quality.precommit 2>&1 | tail -N` several times **and** a
long tail of `gh api … | head -N` calls from the vendor-source survey, which was most of the 27%.

**Ten green claims, and the unpiped re-run exits 0 (551 passed), so all ten hold.** The count is the
second-highest in the corpus after sample 7's seven, on a rate lower than any other row that made
claims at all — which is the corpus's own point restated: the headline number does not predict how
much is riding on it.

[PITFALL: **the one `sed -n` call is the most interesting cell, because it rounds to 0% and is a
straight rule violation.** `sed -n '136,240p'` was used to read a block of `tasks/tools.py` before
moving it, where `Read` with `offset`/`limit` is the tool and the session had been using `Read`
correctly all day. A single call cannot move a rate, so nothing in the scored output distinguishes
"never did this" from "did it once, deliberately, having reasoned about it" — and this instance was
the latter. Read the samples, not only the rates, is the same lesson sample 3's `+0pp` MISS taught
from the opposite direction.]

## What the corpus has settled

**`head/tail` is worse in prose sessions than in code sessions.** Seven samples: 24% code, then 45%,
38%, 55%, 35% and 36% on sessions that spent most of their calls reading files to quote from and
running gates to confirm markdown formatting. The one purely code-shaped session is the one low
rate, and the largest and most purely prose-shaped session is the highest. Sample 7, the one mixed
shape — code and plans in the same run — sits between them at 32%, which is what the split predicts
rather than a counter-example. That points the fix away from wording: `Read` with `offset`/`limit`
is the tool for the quoting half, and the harness's own truncation handles the gate half — neither
is what the rule currently opens on.

**`git -C <own repo>` is a per-session disposition, not a machine-wide trend.** Sample 1's 23% and
sample 3's 0% came from the same repo, the same shape, the same day's rules. Nothing further is owed
on that question.

**The `exit-masked` consequence check works, and has fired clean five times.** `session-harvest`'s
rule — a non-zero `exit-masked` means the session's own green results are unverified, so re-run the
gate unpiped and count how many times the session asserted a green on a masked call:

| sample | `exit-masked` | assertions | what was masked | unpiped re-run     |
| ------ | ------------: | ---------: | --------------- | ------------------ |
| 1      |           19% |          — | not recorded    | exit 0             |
| 2      |           28% |        ~15 | the gate        | exit 0             |
| 3      |           27% |          3 | not recorded    | exit 0             |
| 4      |           32% |          5 | the gate        | exit 0             |
| 5      |            8% |          6 | mostly the gate | exit 0, 643 passed |
| 6      |           27% |          — | listings        | exit 0             |
| 7      |           22% |          7 | the gate        | exit 0             |

Every green held. **"No harm done" is the wrong lesson**: the claims were true and the method could
not have distinguished them from false ones, and sample 2's session pushed five times on that basis.
The count tracks how chatty a session is about its gate rather than how bad the piping is — 27% and
28% produced 3 and ~15 assertions respectively.

**The headline rate cannot tell the three consequences apart, and samples 6 and 7 are the pair that
proves it.** Both are high-rate rows a week apart, and they sit at opposite ends of the distinction:

- **sample 6** — 27%, masked set was read-only listings, damage structurally impossible;
- **sample 2** — 28%, masked gate, and that session **pushed five times** on evidence it could not
  distinguish from false;
- **sample 7** — 22%, masked gate, seven assertions to the user, re-run clean.

Three samples, three different consequences, one number that separates none of them — the lowest of
the three is the one with the most claims riding on it. The `what was masked` column above is
recorded by hand; whether `audit.py` should derive it is the open question below.

**`audit.py`'s `compare` scored absent baseline tags wrongly, and older rows are affected.** A tag
**missing** from the baseline was treated as `0.0`, so a "down" expectation on a pattern added after
the baseline was saved evaluated `0.0 < 0.0` and reported **MISS at a 0% rate**, while other absent
tags collected an equally unearned **OK**. Sample 1 first printed 9/12 for that reason; the honest
figure is 9/11. Fixed in `agent-skills` on 2026-09-02, with `"zero"` expectations still judged (they
are absolute and need no baseline) and only `"down"` ones skipped as `(new)`. **Any adherence figure
quoted from a run whose baseline predates the pattern is affected, in both directions** — re-read
rather than re-trusted if an older sample's score is ever compared against a newer one.

## Open questions

[NEEDS CLARIFICATION: **the gate may be the fix rather than the discipline.**
`inv quality.precommit` prints ~45 lines on success, of which the informative part is the last four,
and it is the single biggest contributor to `head/tail` and `exit-masked` in samples 2, 4 and 5
independently. Two levers that do not depend on anybody remembering: a quieter default that prints a
summary on success and the whole thing on failure, or a documented
`inv quality.precommit > log 2>&1` shape with a Read of the log — which the global rules already
prefer and which the sessions demonstrably do not reach for. Sample 2's falsification kills the
"output is truncated so the filter buys something" argument for a `--quiet` flag, but not the
readability argument.]

[NEEDS CLARIFICATION: **should the corpus carry a second column for _what_ was masked — and should
it count calls or assertions?** Sample 6 asked the first half: seven samples in, the headline number
is stable at 8–32% and does not distinguish a masked gate from a masked `--help`, which have
completely different consequences — a masked gate is a wrong answer published, a masked listing is a
style violation with no possible victim. A `--gate-only` mode in `audit.py` would have separated
sample 6 from samples 2 and 7 on the first pass. Sample 7 sharpens it into the second half: it
masked 22% of calls but made **seven** green claims, and it is the claims that reach the user — a
run that masks forty listings and asserts nothing has no reader, while one that masks a single gate
and says "green" once does. `harvest.py claims` already counts assertions, so the number exists; the
question is whether the corpus wants it as a column or whether it belongs only in the harvest
report. Either way this is an `audit.py` change and **belongs in `agent-skills`**, filed there
rather than decided here.]

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

[NEEDS CLARIFICATION: **should `exit-masked` join `EXPECTATIONS`?** It is measured, reported and now
has a documented consequence in `session-harvest`, but it is scored by nothing, so a run that halves
it gets no credit and one that doubles it produces no MISS. Against: it is a symptom of `head/tail`
rather than an independent habit, and scoring both double-counts one behaviour.]

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
`~/AGENTS.md`.

`2026-09-02-rg-replace-flag-used-twice-in-one-session.md` is a separate finding of the same "simply
not followed" kind and is deliberately not merged here — it is one flag with its own proposed
counter, not a session-level rate.
