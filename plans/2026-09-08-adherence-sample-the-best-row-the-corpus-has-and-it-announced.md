---
status: idea
updated: 2026-09-08
---

# Adherence sample: the best row the corpus has, from an announcing auto-mode session

Filed for merging into `plans/2026-09-02-agents-md-adherence-sample-corpus.md`, the way every other
sample row has been. Kept separate rather than appended because two more rows (14 and 15) are
sitting in the store awaiting absorption at the time of writing, and one merge pass over three is
cheaper and less conflict-prone than three edits to the same table.

## The row

Session `9164dacd-2813-4087-a593-14dc24c44782`, `power-user-linux-setup`, 2026-09-07 14:55Z to
21:15Z — about six hours. Measured with `audit.py` at `95f8af7`, `--until` the harvest boundary,
`--compare 2026-09-06-zero-on-count.json`. **270 calls, 12/13.**

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

**Every headline counter is the corpus best by a clear margin.** `head/tail` at 2% against a
previous low of 5% (sample 12) and a band of 15–55% everywhere else; `chain` at 7% against a range
of 21–64%; `sed-n` and `git-C-own-repo` at a clean zero. `exit-masked` is 2%, and the gate/listing
split says 2 of the 5 masked calls wrapped a gate — with `PIPE_FAIL` in force in this session's
shell, so those greens stood on real exit codes and no gate re-run was owed.

## Why it matters more than "a good row"

**This is an announcing session, and it is the row `2026-08-28-auto-mode-contradicts-bash-rules.md`
has been waiting for.** It opened by stating the resolution out loud — _"Using Read/Edit/Write for
files and `rg` for search despite the auto-mode note — per `~/AGENTS.md`"_ — which is the fifth
occurrence of that pattern and the one that settles the narrow claim. Prior announcing rows scored
file reads at 18%, 15%, 3% and 6%. This one is **0%**: zero `sed-n`, one `cat-view` call in 270.

That plan's standing question was whether an announcement tracks the rule it names or merely
substitutes for it. Across the five rows the answer now looks like **the announcement tracks what it
names and nothing else** — the two `ingesta` rows announced and then read files anyway, while the
three that held (`invoke-stubs`, this repo's 09-07 row, and this one) all did. What this row adds is
the first case where the _unopposed_ rules moved too: `chain` at 7% and `head/tail` at 2% are rules
the auto-mode note says nothing about, and every previous row left them mid-corpus while the
announced half improved.

[NEEDS CLARIFICATION: **so is this an announcement effect at all, or a task-shape effect?** The
corpus's own sample-10 pitfall says a single end-of-session figure is one sample of a rate that
drifts with what the session is doing, and this session was unusually edit-heavy and research-heavy
— long `Edit` runs and clone-and-grep research, both of which are naturally low in chained shell
work. A session that spent six hours on installer debugging would chain more whatever it announced.
The corpus cannot separate the two without a row that announces and does shell-shaped work, which
nothing has yet supplied.]

## The one miss, and it is the interesting one

`rg-replace-bundle = 1`: a single `rg -rn --stats -l` in the first hour, where `-r` ate the `n` and
the flags never applied. **It was caught by the documented detection signature and announced in the
conversation within one call** — the output shape was wrong for what had been asked — and the search
was re-run correctly.

That makes it the third instance recorded against a session that had the rewritten clause in
context, after the two in `plans/2026-09-02-rg-replace-flag-used-twice-in-one-session.md`'s
2026-09-06 row. The pattern across all three: **the wording does not prevent the bundle, and the
detection signature does catch it.** Worth carrying into that plan's open question about which
mechanism to reach for, since it is now the second consecutive sample where detection worked and
prevention did not.

[PITFALL: **the same session also broke the `| head`/`| tail` rule twice and the `find`-versus-`fd`
rule zero times, while spending its day enforcing the truncation rule on three subagents and writing
a new `~/AGENTS.md` rule about research method.** Both violations were self-caught and announced in
the conversation, which is why the rate is 2% rather than higher — but "authoring a rule is not
evidence of following it" now has a sixth instance, and this one is the mildest form: the author
followed it 98% of the time and still produced the shape. The corpus should stop reading that claim
as being about hypocrisy and start reading it as being about how weak a rule's grip is even at its
strongest.]

## Recommended direction

Merge into the corpus as one row alongside samples 14 and 15 when those are absorbed, and carry the
announcing finding into `2026-08-28-auto-mode-contradicts-bash-rules.md`'s table as its sixth row.
Nothing here argues for a `~/AGENTS.md` change: the rules held, and the one that did not is already
owned by its own plan.
