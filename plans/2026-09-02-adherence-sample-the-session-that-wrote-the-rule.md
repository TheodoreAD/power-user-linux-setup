---
status: idea
updated: 2026-09-02
source_repo: github.com-personal/agent-skills
source_session: 13aa58df-3551-49b7-ac0e-0c3693bf8221.jsonl
source_moment: 2026-09-02T20:32:51+03:00
---

# Adherence sample 6: the session that spent the day writing the anti-masking rule

**Merge into `plans/2026-09-02-agents-md-adherence-sample-corpus.md` as sample 6** rather than
keeping it separate — it is another row of that corpus, not a new topic. Filed as its own file only
because it comes from a session in another repo.

## The measurement

`audit.py --session 13aa58df --until 2026-09-02T20:32:51+03:00 --compare 2026-08-24-auto-mode.json`,
opus-5, **216 Bash calls** before the harvest's own sweep (226 including it):

| tag                    | this session | baseline delta | verdict |
| ---------------------- | -----------: | -------------: | ------- |
| `chain`                |          50% |         −17 pp | OK      |
| `head/tail`            |          36% |          +6 pp | MISS    |
| `exit-masked`          |          27% |              — | —       |
| `heredoc`              |          17% |          +1 pp | MISS    |
| `sed-n`                |          11% |          +3 pp | MISS    |
| `cat-view`             |           2% |          +1 pp | MISS    |
| `git-C-mutating`       |           2% |          −0 pp | MISS    |
| `cd-own-repo`          |           1% |          −3 pp | OK      |
| `redirect-then-filter` |           0% |              — | OK      |
| `git-C-own-repo`       |           0% |              — | OK      |

**6 of 11 expectations met.** Both figures reported per the `--until` rule: 36% during the work, 35%
including the sweep — the direction that run happened to lean, and the reason the rule says to
report both rather than to claim the sweep inflates anything.

## Why this sample is worth a row rather than a footnote

**The session's entire subject was this rule.** It shipped `harvest.py` with "nothing runs through a
shell, so no pipe can eat an exit code" as a design principle, wrote the `exit-masked` consequence
rule into `session-harvest`, added `fitness.py derivable` to audit skills for exactly this class of
hand-composed command — and produced `2>&1 | head` in **36%** of its own calls, with 27% masking an
exit code.

That is the third independent confirmation of the corpus's sharpest claim: **authoring a rule is not
evidence of following it, and may not even correlate.** Samples 2 and 3 were sessions that had the
rule in context; this one had the rule as its deliverable.

**The mitigating half, stated so the row is not read as worse than it is:** almost every masked call
was a read-only listing (`plans.py list 2>&1 | head -60`, `--help | head -30`) where the exit code
carried nothing. The repo's gate was run unpiped throughout, and the harvest's own re-run of it
exited 0 — so no green claim in that session stands on filtered evidence. The rate is high; the
damage from it was nil. Both facts belong in the corpus, because a corpus of only the alarming half
argues for a rule nobody can follow.

[NEEDS CLARIFICATION: does the corpus want a second column for _what was masked_ — a gate versus a
listing? Five samples in, the headline number is stable at 22–37% and has not yet distinguished the
two, and they have completely different consequences: a masked gate is a wrong answer published, a
masked `--help` is a style violation with no possible victim. If the answer is a `--gate-only` mode
in `audit.py`, that is a change in `agent-skills` and should be filed there rather than decided
here.]
