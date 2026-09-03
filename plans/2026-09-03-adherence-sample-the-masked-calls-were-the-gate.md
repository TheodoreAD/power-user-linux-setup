---
status: idea
updated: 2026-09-03
source_repo: github.com-personal/ingesta
source_session: 7dab6dae-7c67-454f-bba1-981fe3845089.jsonl
source_moment: 2026-09-03T13:47:32+03:00
---

# Adherence sample 7: the masked calls were the gate, and the greens held anyway

**Merge into `plans/2026-09-02-agents-md-adherence-sample-corpus.md` as sample 7** rather than
keeping it separate — another row of that corpus, not a new topic. Filed as its own file only
because it comes from a session in another repo.

**It is filed chiefly to answer sample 6's open question with data**, not for the headline rate.
That question asks whether the corpus wants a second column for _what_ was masked — a gate or a
listing — on the grounds that five samples in, the headline number had not distinguished them. This
session is the opposite end of that distinction from sample 6, in the same week, and the pair is
what makes the column worth having.

## The measurement

`audit.py --session 7dab6dae --until 2026-09-03T13:47:32+03:00`, opus-5, **129 Bash calls** before
the harvest's own sweep (142 including it):

| tag                     | this session | verdict |
| ----------------------- | -----------: | ------- |
| `chain`                 |          49% | —       |
| `head/tail`             |          32% | MISS    |
| `exit-masked`           |          22% | —       |
| `heredoc`               |          19% | MISS    |
| `git-mutating-in-chain` |           8% | MISS    |
| `chain5`                |           3% | —       |
| `cat-view`              |           1% | MISS    |
| `sed-n`                 |           0% | OK      |
| `cd-own-repo`           |           0% | OK      |
| `git-C-own-repo`        |           0% | OK      |
| `redirect-then-filter`  |           0% | OK      |

A fourteen-hour session in `ingesta`: four plan steps built, one plan retired, twelve commits.

## Why this row answers sample 6's question

**Sample 6's mitigation does not apply here, and that is the finding.** That sample recorded 27%
`exit-masked` and then said, correctly, that "almost every masked call was a read-only listing
(`plans.py list 2>&1 | head -60`, `--help | head -30`) where the exit code carried nothing. The
repo's gate was run unpiped throughout."

This session masked **the gate itself**. `inv quality.precommit 2>&1 | tail -N` was the house shape
for the whole run, along with every `pytest ... 2>&1 | tail -N`. The masked set is not listings with
no possible victim; it is the exact command whose exit code decides whether the work is sound.

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
nothing needs correcting.

That benign outcome is the reason this row is worth recording rather than a reason to skip it. The
corpus now has both halves of the distinction sample 6 asked about:

- **sample 6** — high rate, masked set was listings, damage structurally impossible;
- **sample 2** — `ingesta`, 28%, masked gate, and that session **pushed five times** on evidence it
  could not distinguish from false;
- **this sample** — `ingesta`, 22%, masked gate, seven assertions to the user, re-run clean.

Three samples, three different consequences, one headline number that cannot tell them apart. A
`--gate-only` column would have separated sample 6 from the other two on the first pass.

[NEEDS CLARIFICATION: whether the column should count **assertions** rather than calls. This session
masked 22% of calls but made seven green claims, and it is the claims that reach the user — a run
that masks forty listings and asserts nothing has no reader, while one that masks a single gate and
says "green" once does. `harvest.py claims` already counts them, so the number exists; the question
is whether the corpus wants it as a column or whether it belongs only in the harvest report. If a
column, that is an `audit.py` change and belongs in `agent-skills`.]

## The `head/tail` half, unchanged and unmitigated

32%, against a rule that is unambiguous and was in context the whole time. Nothing new: it is the
same finding the corpus already carries at 25–37% across six samples, and this session adds one more
data point at the low end of that band without changing what it means. No separate filing — this row
is the record.
