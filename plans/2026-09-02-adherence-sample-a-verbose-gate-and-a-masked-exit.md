---
status: idea
updated: 2026-09-02
source_repo: github.com-personal/ingesta
source_session: bf19d40e-bb8f-4341-a396-77194e946991.jsonl
source_moment: 2026-09-02T03:05:26+03:00
---

# Adherence sample: a verbose gate, and 28% of exits thrown away

For the `~/AGENTS.md` adherence watch. One sample, from a ten-hour `ingesta` session — 137 Bash
calls before the harvest boundary, 161 including the sweep.

**Filed alongside
[the same day's other sample](2026-09-02-adherence-sample-first-run-under-the-until-rule.md) rather
than added to it**, because that file was committed **24 seconds** after this harvest took its
boundary — a concurrent harvest was holding it, which is exactly the case `plan-docs` says to add a
file for instead of editing. The two are complementary rather than duplicate: that session's
dominant miss is `git -C <own repo>` at 23% with `head/tail` at 24%, and this one is the mirror
image.

## The numbers

`audit.py --session … --until <boundary>`, against the `2026-08-24-auto-mode.json` opus-5 row
(n=1676):

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

Including the sweep: `head/tail` 42%, `exit-masked` 25% — so the sweep **lowered** both, which is
the direction the `--until` rule says not to assume. Consistent with the 2026-09-01 finding that the
harvest moves the figure either way depending on what it happened to inspect.

## The mechanism, which is not the one already on file

Both misses come from **one shape, produced 15+ times: `inv quality.precommit 2>&1 | tail -N`.** The
session knew the rule — it is in `~/AGENTS.md`, in context, and this session had read it — and
produced the banned shape anyway, at nearly half of all calls. So this is the "simply not followed"
kind rather than the "reasoned around" kind, and the interesting part is _why_ a session that can
quote the rule still types it.

**The obvious explanation is that the gate is too verbose to read plain, and it was tested and is
false.** The hypothesis was that `inv quality.precommit` — fixer, then full check, then `pytest`,
with `pty=True` and colour — emits more than the harness will show, and that the harness truncates
the middle and keeps the head, hiding the verdict; on that reading the filter buys the one thing
being looked for and the fix is a `--quiet` mode on the gate.

**`seq 1 4000` came back complete, all four thousand lines, no truncation and no elision.** So a
plain `inv quality.precommit` would have delivered its verdict, last, in full, every one of those
fifteen times. The filter was buying **nothing** — it was not even trading the exit code for
readability, it was discarding the exit code for free.

That kills the flattering diagnosis and the feature request with it. What is left is worse and
simpler: **the pipe is a reflex, not a response to anything.** It is typed while reasoning about the
next edit, on a command whose output nobody intends to read past the verdict — and the rule against
it is in `~/AGENTS.md`, was in this session's context throughout, and had been read. So the lever is
not wording, not a `--quiet` flag, and not this session knowing more. Which leaves measurement, and
the row above is the contribution.

**Recorded as a self-correction because the correction is the finding.** This plan asserted the
verbose-gate mechanism before checking it, in the same run whose whole subject is a rule being
missed — and it was caught only by running the harness check the skill prescribes. An unchecked
mechanism in a filed plan would have sent whoever picked it up to build a `--quiet` flag that fixes
nothing.

## What the masked exits actually cost, checked rather than assumed

`session-harvest`'s rule fired: `exit-masked` non-zero means the session's own green results are
unverified. Re-run unpiped — `inv quality.check > log 2>&1; echo $?` — came back **`GATE_EXIT=0`**,
so every green this session reported was in fact green.

**Worth stating precisely, because "no harm done" is the wrong lesson.** The claims were true and
the method could not have distinguished them from false ones. The session reported "gate green"
perhaps fifteen times on evidence that had already been discarded, and it pushed five times on that
basis. It got the right answer by luck, and the audit is the only thing that can tell those apart
afterwards.

Two `git push 2>&1 | tail` calls are the same class on an outward-facing command — both pushes did
succeed, confirmed independently by CI.

[NEEDS CLARIFICATION: what the actual output ceiling is, since 4000 lines is a floor rather than the
limit. The falsification above only shows the gate's output is comfortably under whatever the limit
is, which is enough to kill the verbose-gate story but not enough to say the filter is never
justified. A one-line probe at 20k and 100k lines would establish where truncation begins and which
end it keeps — worth knowing once, machine-wide, because every session reaches for this filter and
none of them can currently say whether it is ever the right call.]

[NEEDS CLARIFICATION: whether `head/tail` correlates with anything measurable at all, now that
output volume is out. Candidates: session length (this one ran ten hours), the proportion of calls
that are `inv`/`git` verdict-checks rather than reads, or nothing — a flat rate across shapes would
say it is a pure reflex and that only a mechanism firing at type-time can move it. `--days` across
sessions answers it; three samples now exist for 2026-09-01/02 alone.]
