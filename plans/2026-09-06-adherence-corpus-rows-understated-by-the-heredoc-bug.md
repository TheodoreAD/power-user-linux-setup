---
status: idea
updated: 2026-09-07
source_repo: github.com-personal/agent-skills
source_session: c3ef9832-a5b8-4d99-932b-2597c5846af6.jsonl
source_moment: 2026-09-06T03:13:26+03:00
---

# The adherence corpus's rates are understated wherever a session wrote patch heredocs

## Context

`plans/2026-09-02-agents-md-adherence-sample-corpus.md` in this repo carries samples measured with
`session-bash-audit`'s `audit.py` — seven when this was written on 2026-09-06, **rows 1–11** by the
time the decision below was taken, with sample 12 the first measured after the fix and therefore the
only one already comparable with a re-scored corpus. **The instrument was under-counting, and every
row before 12 inherits the error.**

`audit.py`'s `strip_heredoc` cut the command at the heredoc marker and returned everything before
it, so it dropped the body **and every command that followed it**. The shape that loses is the one
this family writes constantly — a patch heredoc, then the gate:

```
python3 - <<'PY'
...
PY
inv quality.precommit 2>&1 | tail -30
```

The pattern table saw `python3 -`. Every predicate builds on that function, so the loss is uniform
across the rows rather than confined to one. Fixed in `agent-skills` on 2026-09-06 (`2248ec7`), with
the dated evidence in that skill's `references/research.md`.

## What it does to this corpus

Measured over the 7 days to 2026-09-06, 15,479 Bash calls: 1,267 tag hits were invisible across 30
sessions — 437 `head/tail`, 381 `exit-masked`, 218 `grep/find`. Corpus-wide the rates move
`head/tail` 25.0% -> 27.8% and `exit-masked` 15.3% -> 17.8%, but the calls concentrate in sessions
that drive edits through scripts, so **per session the correction reached +12pp**.

**Sample 6 is one of the affected sessions.** Transcript
`13aa58df-3551-49b7-ac0e-0c3693bf8221.jsonl`, recorded in the corpus at 27% `exit-masked`; re-scored
at the row's own `--until` boundary it is **38%**.

[PITFALL: **this section first said 37%, and 37% is the whole-transcript figure — a different
measurement, not a correction of this one.** 37% is 252 calls; the row's boundary is 216, and at
that boundary the answer is 38%. `agent-skills`' `skills/session-bash-audit/references/research.md`
carried the same error ("recorded at 27% against a real 37%") and was corrected there 2026-09-07.
Cite 38%.]

That row is load-bearing beyond its own cell. `agent-skills`'
`plans/2026-09-04-exit-masked-needs-a-gate-versus-listing-column.md` uses sample 6 as "the cleanest
possible case of a high rate that means nothing" — the anchor for the argument that a high
`exit-masked` needs a gate-versus-listing split before it can be read. The anchor's real rate is
eleven points higher than the argument was built on. Whether the argument survives is a separate
question from whether the number was right; it was not.

Four other sessions in the same week moved comparably (20% -> 32%, 26% -> 39%, 17% -> 28%, 14% ->
25%), which is what makes this a corpus-shaped problem rather than one bad row: any sample taken
from a heredoc-heavy session is understated by the same mechanism, and this family's sessions are
heredoc-heavy by habit.

## Evidence

The fix, its measurement and its tests are in `agent-skills`:

- `skills/session-bash-audit/scripts/audit.py` — `strip_heredoc`, commit `2248ec7`
- `skills/session-bash-audit/references/research.md` — "A heredoc hid every command that followed it
  (2026-09-06)", commit `27f96eb`
- `plans/2026-09-06-audit-strip-heredoc-drops-the-rest-of-the-command.md` — the working plan, which
  carries this same question as its one remaining `NEEDS CLARIFICATION`

Session `c3ef9832-a5b8-4d99-932b-2597c5846af6.jsonl` in `agent-skills`, from 2026-09-06T00:30+03:00
onward. Distinctive phrase: "the two instruments' disagreement, which is what surfaced this".

The finding arrived sideways and the route is worth keeping: `session-harvest`'s `claims` matches
the raw command with its own copy of the `exit-masked` regex, so the two skills disagreed on the
same-named counter. 390 calls in the week were tagged by `harvest` and not by `audit`; 388 of them
were this bug. **Two instruments over one corpus is how a defect in either becomes visible** — a
single instrument is only ever self-consistent, which is the general lesson for a corpus that scores
itself with one script.

No user correction prompted this. It came out of taking step 1 of the gate-versus-listing plan
("check what `harvest.py claims` already produces before adding anything to `audit.py`"), which
answered a different question than it asked.

## The decision, taken with the user 2026-09-07

**Re-score rows 6, 7 and 11. Annotate the rest as floors.** Merged in from
`plans/2026-09-07-adherence-corpus-rescore-decision-and-boundary-numbers.md`, filed from
`agent-skills` — which owns the instrument and not the corpus — so the session applying it needs no
re-measurement. The three re-score-versus-annotate options were put with the measurement below; this
was chosen over annotating everything and over re-scoring everything.

### Why the split is at three rows and not somewhere else

**The corpus's rows are `--until` measurements, and only rows 6, 7 and 11 record the boundary they
used** — the rest record the session start, which is the other end of the same session. Re-scored at
a recorded boundary the denominator reproduces the published `calls` column **exactly**, which is
what makes the new rate a correction of the old one rather than a different measurement:

| #  | transcript  | calls, published | calls, re-scored | `head/tail`   | `exit-masked` |
| -- | ----------- | ---------------: | ---------------: | ------------- | ------------- |
| 6  | `13aa58df…` |              216 |          **216** | 36% → **47%** | 27% → **38%** |
| 7  | `7dab6dae…` |              129 |          **129** | 32% → **38%** | 22% → **28%** |
| 11 | `6291d9d1…` |              228 |          **228** | 24% → **27%** | 7% → **12%**  |

`git-C-own-repo` is unchanged on all three (0%).

[PITFALL: **a whole-transcript re-score is not a correction, and on one row it reads as an
improvement that never happened.** Sample 1 has no recorded boundary: measured whole it is 384 calls
against the row's 331, and `exit-masked` comes out **18% against the published 19%** — lower, after
a fix that can only ever raise the count, because the extra 53 calls were cleaner than the ones in
the original window. Any row re-scored without its boundary changes denominator silently and stops
being comparable with its neighbours, which is the corpus's whole value.]

### Nothing has expired yet, and one row never can be fixed

All eleven recorded transcripts were still on disk on 2026-09-07, checked by id under
`~/.claude/projects/`. That answers the deadline question this plan raised: the ~2026-10-02 expiry
is real but not yet biting, and it is the window this work sits in. **Row 4 can never be re-scored**
— its transcript id was never written down, which makes it the one row the deadline cannot threaten
and the one row nothing can fix.

## What applying it looks like

1. Update rows 6, 7 and 11 of the corpus table with the figures above, and say beside them that they
   were re-measured at their recorded `--until` boundary after the `strip_heredoc` fix.
2. Annotate the other rows — including row 4 — as **floors**: measured with an instrument that
   dropped every command after a heredoc, so a heredoc-heavy session's rate is understated, and the
   boundary needed to correct them was not recorded. Do not re-score them whole-transcript.
3. Anywhere the corpus's own prose leans on sample 6's rate (the gate-versus-listing argument does,
   as "the cleanest possible case of a high rate that means nothing"), check whether 38% still
   carries the argument it was making at 27%. The direction helps that argument rather than hurting
   it, but it is a re-read, not a substitution.
4. Record the instrument commit beside the re-scored rows, which answers this plan's third question
   — `save_baseline` already does this for baselines, and it is the field that makes the next
   instrument change visible instead of silent.

### How the re-scores were run

`agent-skills`' `skills/session-bash-audit/scripts/audit.py` at the post-fix commit, one call per
row, on 2026-09-07:

```shell
audit.py --session 13aa58df-3551-49b7-ac0e-0c3693bf8221 --until 2026-09-02T20:32:51+03:00 --samples 0
audit.py --session 7dab6dae-7c67-454f-bba1-981fe3845089 --until 2026-09-03T13:47:32+03:00 --samples 0
audit.py --session 6291d9d1-b8ed-4826-9967-9ae30f70bebf --until 2026-09-05T10:21:37Z --samples 0
```

The boundaries are the `source_moment` values the corpus already records for those three rows.
