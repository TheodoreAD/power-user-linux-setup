---
status: landed
updated: 2026-09-02
source_repo: github.com-personal/agent-skills
source_session: 13aa58df-3551-49b7-ac0e-0c3693bf8221.jsonl
source_moment: 2026-09-02T15:52:00+03:00
---

# Every commit gets a body, including the one-line ones

## Context

`~/AGENTS.md`'s "About to commit" and "Committing multi-part work" sections say a great deal about
_how_ to pass a commit message (inline `-m`, no backticks, no `-F`, by pathspec) and about _how to
split_ the work, and nothing about what the message must contain. A session reading both correctly
can still produce a subject-line-only commit, and did.

## Evidence

A session in `agent-skills` committed five changes, four with multi-paragraph bodies and one — a
six-line README edit — with a subject line alone:

```
git commit -m "README: session-harvest reads outside the repo too, and now declares it" -- README.md
```

The user rejected the tool call and said, verbatim:

> commits need a description

The re-do with a four-line body was approved immediately. Nothing else about the commit changed, so
the missing body is the whole of what was refused.

The tell for _why_ it happened: the four commits that got bodies were the substantial ones. The
agent scaled the message to the size of the diff, which is exactly the judgement the rule has to
overrule — a small diff is where "why" is least recoverable later, because the diff itself explains
even less.

## Recommended direction

A short paragraph in the "About to commit" section, not a new rule heading — it is a property of the
message, and that section already owns the message's mechanics.

> **Every commit carries a body, not only a subject line.** `git log` is how a future agent learns
> why a change happened, and a one-line message hands it what changed, which the diff already says.
> Say what the commit is for and what it decided; two or three sentences is normal. This holds
> hardest for the small commits — a six-line doc edit is where the reasoning is least recoverable
> from the diff, and where the temptation to skip it is strongest.

## The two questions this opened with, answered

Both were answered by the rule that landed, independently of this plan.

**No stated shape.** The rule requires a body and says nothing about subject length, wrapping or
layout — the narrow form the evidence supports, and the one that does not collide with the existing
prohibition on backticks and `$` inside a double-quoted `-m` argument.

**One exception, and it is not the formatting commit this plan guessed at.** A gate run's formatting
fix still owes a why, exactly as reasoned here. The real exception is a plan filed into the plans
store, which commits as `<repo>: <what it is>` with no body because the filed plan is its own
description and the commit is only its delivery. It is named in the rule rather than left to be
found as an inconsistency.

## What happened instead: it landed from another plan the same day

This plan was filed from `agent-skills` and reached this repo through the store. By the time it was
absorbed (2026-09-02), the rule was already live — admitted hours earlier from
`plans/2026-09-01-every-commit-carries-a-why.md`, on a different session's evidence, and worded
almost exactly as proposed above. It extends "About to commit" rather than taking a heading, so
`git.md` stayed at 8 rules.

Two independent sessions producing the same refusal on the same day, in different repos, is the
substance this plan contributed. The mechanisms were **not** the same, and that is what made it
worth migrating rather than discarding as a duplicate: the other session rationalised the omission
from the plan file already carrying the reasoning, while this one simply scaled the message to the
size of the diff.

## Migrated to

- `contributing/global-agents-md.md`, "Every commit has a body" — the second occurrence, the user's
  verbatim refusal, and the scaled-to-the-diff tell, recorded alongside the first session's
  different rationalisation.
- The rule itself is `config/agents-md/git.md`, "About to commit", deployed as `~/AGENTS.md`. Not
  written by this plan.

Deliberately not migrated: the proposed wording block above, since the deployed rule supersedes it,
and the two answered questions, since the answers are in the rule itself.
