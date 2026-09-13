---
status: idea
updated: 2026-09-13
source_repo: github.com-personal/repo-tasks
source_session: 5de331c8-e7f0-4bcb-a86f-c242683a382d.jsonl
source_moment: 2026-09-13T14:56:10+03:00
source_plan:
---

# An adherence sample whose low chain rate came from skipping the gate the chain is made of

## Context

**This is a delivery, not a new topic.** Two existing plans in this repo own what is below and the
rows belong in them rather than in a file of their own — merge and delete this:

- `plans/2026-09-02-agents-md-adherence-sample-corpus.md` — the sample and the coupling below.
- `plans/2026-09-02-rg-replace-flag-used-twice-in-one-session.md` — a second instance of exactly
  what its title says.

Filed rather than merged because the session that measured it was working in `repo-tasks` and
writing into another repo's tree is out.

## The sample

`audit.py --session 5de331c8 --until 2026-09-13T14:56:10+03:00`, `--compare 2026-09-12.json`. 152
calls over ~29 hours, 12 sweep calls excluded. Claude Opus 5. **14/17 expectations met.**

| tag              |   rate | note                                   |
| ---------------- | -----: | -------------------------------------- |
| `chain`          | **3%** | 5 calls — against 56% and 57% in 14/15 |
| `head/tail`      |     0% |                                        |
| `exit-masked`    |     1% | 2 calls, **0 wrapped a gate**          |
| `cat-view`       |     2% | 3 calls — MISS                         |
| `git-C-mutating` |      2 | MISS — both `git -C ~/plans push`      |
| `rg-replace`     |     1% | 2 calls, `-rn` x2 — MISS               |
| everything else  |     0% |                                        |

`pipefail` confirmed in force by `setopt`, and both masked calls were a read-only probe script that
printed its own exit code in its output, so no green claim rested on a filter.

## The finding, which is not a rate

**The chain rate is an order of magnitude below samples 14 and 15, and part of the reason is that
this session never ran the gate those chains exist for.** Both of those samples attribute their
`chain` figure to one dominant shape — `git add <paths> && plans.py scan --mode staged` before every
commit. This session made **8 commits and 2 pushes to a public repo and ran `plans.py scan` zero
times**, in either mode, before any of them.

So the two measurements are coupled, and the corpus has been reading one of them without the other:

- A session that follows the confidentiality rule pays for it in `chain`, and looks worse.
- A session that skips the rule entirely scores 3% and looks like the corpus's best result to date.

**3% is not evidence of discipline here. It is partly evidence of an omission the audit has no tag
for.** That is worth stating in the corpus plan, because the chain rate is one of its headline
series and this sample would otherwise enter it as an outlier success.

The scan was eventually run, during the session's own harvest and after both pushes: **0 hits over
history against 61 private terms**, so nothing was exposed and the omission cost nothing this time.
That is the reason it is a measurement finding rather than an incident.

[PITFALL: **the omission is invisible to every instrument the corpus uses.** `audit.py` has no tag
for a command that was not run, and a clean `scan --mode history` afterwards looks identical whether
the gate ran before each commit or once at the end. The only reason this surfaced is that the
session's harvest ran the scan for an unrelated reason and the session then noticed it had never run
it during the work. A corpus of sessions measured this way cannot currently distinguish "ran the
gate 8 times" from "never ran it", and the second scores better on the series it does measure.]

## Open questions

[NEEDS CLARIFICATION: does the corpus want a tag for it? A "gate-skipped" row would need `audit.py`
to know which commands are gates for which action — it already has a `GATE_RE`, and that regex is
separately known to have no term for `plans.py scan` (owned by `agent-skills`'
`plans/2026-09-13-gate-re-has-no-term-for-the-confidentiality-scan.md`). Those two are the same
weakness seen from opposite sides: one misclassifies the scan when it runs, the other cannot see it
when it does not.]

[NEEDS CLARIFICATION: is the chained form actually required? The corpus's open question already asks
whether `git add <paths> && plans.py scan --mode staged` is two rules meeting at one point. This
sample adds a third option nobody has priced — commit by pathspec and run the scan as its own call,
which satisfies both rules and chains nothing. Whether that is what the rule should recommend is
this repo's call, not the sample's.]

## The second row: `rg -r` again

Two occurrences, both `-rn`, both in the same twenty minutes while reading a vendor clone:
`rg -rn --files-with-matches 'UV_PYTHON' <dir>` and `rg -rn 'struct ToolPython' <dir>`.

**Both were caught by the session itself and re-run correctly**, and both were caught by the exact
detection signature the rule documents — output that did not look like what was asked for
(`pub(crate) n {` where a struct declaration should have been). So this instance is evidence that
the detection half of the rule works, and that the prohibition half did not prevent the shape in a
session that had the rule in context the whole time.

That is the distinction `2026-09-02-rg-replace-flag-used-twice-in-one-session.md` should probably
carry: same count, same session shape, and this time with the recovery observed rather than
inferred.
