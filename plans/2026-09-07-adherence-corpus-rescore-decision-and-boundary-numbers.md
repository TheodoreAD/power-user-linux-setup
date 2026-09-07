---
status: idea
updated: 2026-09-07
source_repo: github.com-personal/agent-skills
source_moment: 2026-09-07T09:20:00Z
---

# The corpus re-score is decided, and three rows are measured — apply them here

Filed from `agent-skills`, which owns the instrument and not the corpus. It answers the open
question in this repo's own
[`2026-09-06-adherence-corpus-rows-understated-by-the-heredoc-bug.md`](2026-09-06-adherence-corpus-rows-understated-by-the-heredoc-bug.md)
and carries the numbers, so the session that applies it needs no re-measurement. **Filed rather than
applied because the corpus is this repo's file**; nothing in this repo was touched.

## The decision, taken with the user 2026-09-07

**Re-score rows 6, 7 and 11. Annotate the rest as floors.** The three re-score-versus-annotate
options were put with the measurement below; this was chosen over annotating everything and over
re-scoring everything.

## Why the split is at three rows and not somewhere else

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

[PITFALL: **the 37% already published for sample 6 is the whole-transcript figure.** `agent-skills`'
`skills/session-bash-audit/references/research.md` said "recorded at 27% against a real 37%"; 37% is
252 calls, the whole transcript. At the row's own boundary it is 216 calls and **38%**. Corrected in
that repo 2026-09-07, in the same pass that filed this. Cite 38% here.]

## Also settled: nothing has expired yet

All eleven recorded transcripts were still on disk on 2026-09-07, checked by id under
`~/.claude/projects/`. **Row 4 can never be re-scored** — its transcript id was never written down,
which is the one row the deadline cannot threaten and the one row nothing can fix. The ~2026-10-02
expiry is real but not yet biting; that is the window this work sits in.

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
4. `2026-09-06-adherence-corpus-rows-understated-by-the-heredoc-bug.md` can then close its three
   open questions: this decides the first, the transcript check answers the second, and the third —
   whether the corpus records which instrument measured each row — is answered by recording the
   instrument commit beside the re-scored rows, which `save_baseline` already does for baselines.

## Evidence

Re-scores run 2026-09-07 with `agent-skills`' `skills/session-bash-audit/scripts/audit.py` at the
post-fix commit, one call per row:

```shell
audit.py --session 13aa58df-3551-49b7-ac0e-0c3693bf8221 --until 2026-09-02T20:32:51+03:00 --samples 0
audit.py --session 7dab6dae-7c67-454f-bba1-981fe3845089 --until 2026-09-03T13:47:32+03:00 --samples 0
audit.py --session 6291d9d1-b8ed-4826-9967-9ae30f70bebf --until 2026-09-05T10:21:37Z --samples 0
```

The boundaries are the `source_moment` values the corpus already records for those three rows.
