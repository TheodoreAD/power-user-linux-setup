---
status: idea
updated: 2026-09-07
source_repo: github.com-personal/repo-tasks
source_session: 52905ee0-50ff-4376-bd19-5ab4d9ca0a24.jsonl
source_moment: 2026-09-07T19:12:55+03:00
---

# Adherence sample: the session that authored a detection rule and broke four Bash rules writing it

**A row for [the sample corpus](2026-09-02-agents-md-adherence-sample-corpus.md), not a plan of its
own** — filed rather than appended because the corpus lives in this repo and a session in another
one may not write here. Absorb it into that plan's tables and delete this file.

What earns it a row rather than a mention: it is the **highest-`chain` session measured so far** and
the first where `git-C-own-repo` and `head/tail` were both in their worst band at once, in a session
whose subject was writing deterministic detection for a coupling rule. The corpus's own framing —
"authoring a rule is not evidence of following it" — has a sharper instance here than the one that
produced the phrase.

## Evidence

Transcript
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-repo-tasks/52905ee0-50ff-4376-bd19-5ab4d9ca0a24.jsonl`,
session start `2026-09-06T00:11:27.349Z` (the working part of it began 2026-09-07T11:00 after a
`/clear`). Measured at the harvest boundary `2026-09-07T19:12:55+03:00`, so the sweep's own 14 calls
are excluded.

| #  | session repo   | calls | shape                             | `head/tail` | `exit-masked` | `git-C-own-repo` |
| -- | -------------- | ----: | --------------------------------- | ----------: | ------------: | ---------------: |
| 14 | `repo-tasks`   |   372 | code+prose, one repo, eight hours |     **42%** |       **25%** |          **19%** |
| 15 | `agent-skills` |   196 | code+prose, one repo, ~11.5 hours |         28% |       **23%** |               0% |

The rest of `audit.py`'s table for the same window: `chain` **56%** (210), `chain5` 5% (18),
`heredoc` 13% (49), `git-C-mutating` 55, `git-mutating-in-chain` 20, `search|head` 19% (72), `sed-n`
1% (5), `cat-view` 1% (5), `cd-own-repo` 0%, `grep-r-not-rg` 0%, `find-not-fd` 0%.

Three things in that row are worth the corpus's attention beyond the numbers:

- **`exit-masked` 25% (93 calls), of which 74 wrapped a gate.** `pipefail` was in force (`setopt`
  answered `pipefail` in this session's own shell), so the seven green-gate claims the session made
  stood on real exit codes and no re-run was owed. The gate/listing split is what made that a
  two-line check rather than a re-run — it is the first sample where the split existed and was above
  zero on the gate side.
- **`git-C-own-repo` 19% — 71 calls, 55 of them mutating.** The rule names this as the commoner
  mistake than the `cd` it replaced, and `cd-own-repo` was indeed 0%. Every one of the 71 was
  against the session's own repo, which is the shape the rule is about.
- **`chain` 56%** is mostly one habit: `git add <paths> && plans.py scan --mode staged`, repeated
  before every commit, plus `inv quality.precommit 2>&1 | tail -N && git add …`. The scan-before-
  commit rule and the one-command-per-call rule pull against each other at exactly that point, and
  the session resolved it the wrong way ~20 times in a row without noticing.

### Row 15, added 2026-09-07 — and it answers the first open question below

Transcript
`~/.claude/projects/-home-tdumitrescu-projects-github-com-personal-agent-skills/af52116e-18ca-4557-9fbe-86cec225fe3e.jsonl`,
session start `2026-09-07T12:07:35.439Z`, boundary `2026-09-07T23:43:57+03:00` (8 sweep calls
excluded). The rest of the table: `chain` **57%** (112), `chain5` 11% (21), `heredoc` 6% (11),
`git-C-mutating` 1, `git-mutating-in-chain` 12, `search|head` 5% (10), `sed-n` 1% (2), `cat-view` 1%
(1), `cd-own-repo` 1, `grep-r-not-rg` 0%, `find-not-fd` 1%. `pipefail` in force, 5 green-gate
claims, all on real exit codes.

**Row 14's first open question is no longer a single observation.** `chain` 57% here, in a different
repo on a different subject, is dominated by the same seam:
`git add <paths> && plans.py scan --mode
staged` before every commit. Two sessions, two repos, 56%
and 57%, same cause — so the question "is a chain that exists because two rules meet the same
finding as a chain of convenience?" now has a second instance and should be decided rather than
carried. The fix belongs to one of the two rules naming what to do at the seam; nothing about the
sessions differed.

**A second finding, and it is about rule efficacy rather than a rate.** `~/AGENTS.md` states, with
the exact command and the exact failure, that `gh run list --commit <7-char-sha>` prints `[]` and
exits 0 because `--commit` matches only the full 40-char SHA, so an `until` loop over it can never
become true and "still running" is indistinguishable from "will never finish". This session
reproduced that **verbatim** — short SHA, `until` loop, the wait moved to the background at its
timeout — while the rule sat in its context. It is the sharpest available instance of the corpus's
"authoring a rule is not evidence of following it", one step further along: _reading_ a rule that
names the command, the failure and the mechanism is not evidence either. The recovery was cheap
(`git rev-parse HEAD`), which is what makes it easy to under-weight.

## Open questions

[NEEDS CLARIFICATION: the `chain` figure is dominated by a _pair_ of rules interacting — "run
`plans.py scan --mode staged` immediately before the commit" and "one command per call" — and the
corpus has no column for that. Is a chain that exists because two rules meet at one point the same
finding as a chain of convenience? They have different fixes: the second is a habit, the first wants
one of the two rules to say what to do at the seam.]

[NEEDS CLARIFICATION: whether this row belongs in the corpus at all given
`2026-09-02-rg-replace-
flag-used-twice-in-one-session.md` already exists and this session hit the
`rg -r` trap **twice** more (caught both times, once by the output looking wrong and once by
recognising the shape). That plan owns the pattern; this row would only add "twice more, in a
session that had read the rule", which may be a line in that plan rather than a column here.]

## Recommended direction

Absorb as row 14 with the three notes above kept — particularly the `exit-masked` one, since it is
the first sample where the gate/listing split answered the question that used to need a gate re-run.
Then decide the first open question, because a 56% chain rate that is mostly one two-rule seam is a
finding about the rules rather than about the session, and the corpus currently cannot express that.
