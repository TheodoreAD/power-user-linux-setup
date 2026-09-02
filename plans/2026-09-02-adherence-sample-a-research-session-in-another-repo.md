---
status: idea
updated: 2026-09-02
---

# Adherence sample: a research session, in a repo the corpus has not sampled

## Context

Fifth sample of the day, and the first from **`ingesta`** rather than from `power-user-linux-setup`
— which is the reason it is worth recording separately rather than folded into the existing four.
Every prior sample is a session working on the tooling repos themselves; this one is a long
domain-research and plan-writing session in a project repo, so the task shape differs as well as the
codebase.

Session `6be217e8`, 2026-09-02, `claude-opus-5`, auto mode. Roughly three and a half hours: reading
vendored reference clones, web research on clinical guidelines, and writing four plan files plus
`AGENTS.md` and `contributing/` edits. Ten commits, no pushes.

## The numbers

Taken with `--until` at the harvest boundary, so the sweep is excluded: **84 calls** during the
work, 22 more in the sweep.

| counter                 | this session | baseline (2026-08-24, n=1676) | verdict         |
| ----------------------- | ------------ | ----------------------------- | --------------- |
| `chain`                 | 37%          | 66%                           | −29pp, OK       |
| **`head/tail`**         | **35%**      | 31%                           | **+4pp, MISS**  |
| `exit-masked`           | 8%           | 11%                           | OK on the delta |
| `sed-n`                 | 4%           | 8%                            | OK              |
| `cat-view`              | 1%           | 2%                            | OK              |
| `heredoc`               | 0%           | 16%                           | OK              |
| `cd-own-repo`           | 0%           | 3%                            | OK              |
| `git-C-own-repo`        | 0%           | 0%                            | OK              |
| `git-mutating-in-chain` | 0%           | 8%                            | OK              |

10 of 11 expectations met. The single miss is `head/tail`, and `chain5`, `redirect-then-filter`,
`cd-own-repo` and every git counter are clean — notably `git-mutating-in-chain` at 0% across ten
commits, all made by pathspec in their own calls.

**Including the sweep: `head/tail` 40%, `exit-masked` 12%.** The sweep raised both, which is the
opposite direction from the 2026-09-02 verbose-gate sample where it lowered them — consistent with
that plan's point that the sweep's effect is a property of the run rather than a bias with a sign.

## What the misses actually were

**`head/tail` (29 calls) splits into two populations that deserve different treatment.** Roughly
half are `rg … | head -N` over vendored reference clones in `$RESEARCH_HOME` — searching an
unfamiliar third-party codebase, where the honest alternative is `rg -c` first and the session did
not reach for it. The other half are `inv quality.precommit 2>&1 | tail -N`, which is the gate case
and is the one that matters.

**`exit-masked` (7 calls) is almost entirely that same gate**: six runs of
`inv quality.precommit 2>&1 | tail -N`, plus one `inv web.read 2>&1 | tail -80`.

Per `session-harvest`'s rule the gate was re-run unpiped at harvest time: **exit 0, 643 passed**, so
every masked green held. The session had asserted "gate green" to the user **six times**, five of
them from masked calls — all five true, which is the outcome that makes the rule easy to skip and
the reason it is written as a count rather than a warning.

## Open questions

[NEEDS CLARIFICATION: **The gate is the single biggest contributor to both misses, and the fix may
be the gate rather than the discipline.** `inv quality.precommit` prints ~45 lines on success, of
which the informative part is the last four. Every masked call in this session exists because a
session wanted the tail of a verbose success. The verbose-gate sample from the same day reached the
same place independently. Two levers that do not depend on anybody remembering: a quieter default
that prints a summary on success and the whole thing on failure, or a documented
`inv quality.precommit > log 2>&1` shape with a Read of the log — which the global rules already
prefer and which the sessions demonstrably do not reach for.]

[NEEDS CLARIFICATION: **Whether reading unfamiliar third-party source is a legitimate `head` case
that the counter should distinguish.** Half this session's `head/tail` calls were exploratory greps
over vendored clones where the result set size was genuinely unknown. The rule's own answer is
"count first with `rg -c`", which is two calls where one was wanted, and the counter cannot tell
that population from the gate one. Worth knowing whether the corpus splits the same way, because the
two have different fixes and only one of them is a discipline problem.]

## Recommended direction

Fold into the existing adherence corpus as the fifth sample. The genuinely new information is the
repo and the task shape, and the one claim worth carrying forward is that `head/tail` here is two
populations rather than one — which is a partial answer to the open question the verbose-gate plan
raised about whether `head/tail` correlates with anything measurable.
