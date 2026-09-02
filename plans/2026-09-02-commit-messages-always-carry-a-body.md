---
status: idea
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

[NEEDS CLARIFICATION: does this deserve a stated shape (subject under ~72 chars, blank line, body
wrapped) or only "there must be a body"? The observed failure was an absent body, not a malformed
one, so the narrow rule is what the evidence supports. A format rule would also collide with the
existing prohibition on backticks and `$` in a double-quoted `-m` argument, which is the part that
actually breaks things.]

[NEEDS CLARIFICATION: is there a genuine exception? A pure formatting commit from a gate run
("dprint reflow") is the candidate — but the existing rules already ask that one to say _why_ an
unrelated file was touched, which is a body. Probably no exception, stated as none.]
