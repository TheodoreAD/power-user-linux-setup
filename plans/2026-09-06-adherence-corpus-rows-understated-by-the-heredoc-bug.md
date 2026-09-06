---
status: idea
updated: 2026-09-06
source_repo: github.com-personal/agent-skills
source_session: c3ef9832-a5b8-4d99-932b-2597c5846af6.jsonl
source_moment: 2026-09-06T03:13:26+03:00
---

# The adherence corpus's rates are understated wherever a session wrote patch heredocs

## Context

`plans/2026-09-02-agents-md-adherence-sample-corpus.md` in this repo carries seven samples measured
with `session-bash-audit`'s `audit.py`. **The instrument was under-counting, and the corpus rows
inherit the error.**

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
`13aa58df-3551-49b7-ac0e-0c3693bf8221.jsonl`, recorded in the corpus at 27% `exit-masked`; re-tagged
with the fixed instrument it is **37%**.

That row is load-bearing beyond its own cell. `agent-skills`'
`plans/2026-09-04-exit-masked-needs-a-gate-versus-listing-column.md` uses sample 6 as "the cleanest
possible case of a high rate that means nothing" — the anchor for the argument that a high
`exit-masked` needs a gate-versus-listing split before it can be read. The anchor's real rate is ten
points higher than the argument was built on. Whether the argument survives is a separate question
from whether the number was right; it was not.

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

## Open questions

[NEEDS CLARIFICATION: **re-score the affected rows, or annotate them?** Re-scoring changes published
numbers and makes the seven rows comparable again, which is the corpus's whole value; annotating
leaves them wrong but traceable and costs nothing. A third option is to re-score and keep the old
figure in the same cell, which preserves the delta as its own evidence — this repo's own baseline
practice is that the deltas are the point.]

[NEEDS CLARIFICATION: **which rows can still be re-scored at all?** Three of the seven transcripts
expire around 2026-10-02 (the harness keeps 30 days by default). Sample 6's is one of them, and it
is the row that most needs the correction. A row whose transcript is gone can only be annotated, so
the answer may differ per row — and the deadline is real rather than notional.]

[NEEDS CLARIFICATION: **does the corpus record which instrument measured each row?** A baseline
saved before 2026-09-06 cannot be read against one saved after — both headline rows moved by about
the size of a real regression while no session changed. `save_baseline` records the instrument
commit for exactly this reason; the corpus's sample rows may want the same field, or this problem
recurs silently at the next instrument fix.]

## Recommended direction

1. Re-score sample 6 first, while its transcript exists, and see whether the gate-versus-listing
   argument still holds with the corrected rate in front of it.
2. Decide re-score-versus-annotate for the rest by transcript availability rather than in the
   abstract.
3. Add the instrument commit to each row, whichever way 1 and 2 go — it is the field that makes the
   next instrument change visible instead of silent.
