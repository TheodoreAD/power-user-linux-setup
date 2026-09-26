---
status: idea
updated: 2026-09-26
---

# A delegated-research prompt has to say "do not fan out", for the same reason it says "clone and grep"

## Context

Session `f7cff2a9`, 2026-09-21, evaluating four third-party tools for an AI dev stack. Six research
subagents were spawned deliberately, against a budget reasoned about as six. **Twelve ran.** Four of
the six independently parallelised their own briefs, spawning six more between them, and the session
hit `You've hit your session limit` (HTTP 429). Seven agents terminated mid-flight.

What it cost: two of six research areas lost entirely, one returning only two of its four
sub-reports. The OpenCode research — the subject of a direct user question earlier in the session —
came back as nothing and had to be redone by hand from the clone afterwards, which took about
fifteen minutes and produced a better answer than the agent would have. So the loss was recoverable
here; the point is that nothing said it was about to happen.

## Why this is the delegated-research clause again, not a new rule

`config/agents-md/research.md` already carries the shape, under "About to fetch a page or file to
learn how something works":

> The same applies to **any research you delegate**. A subagent never loads this file, so a prompt
> that does not say "clone into `$RESEARCH_HOME` and grep locally" gets page-at-a-time fetching, and
> the fault is the prompt's.

The fan-out case is that sentence with one word changed. A subagent never loads the file, so a
prompt that does not say "do not spawn subagents" gets subagents — and the fault is the prompt's.
Same mechanism, same owner, same remedy.

Evidence that the existing clause works when it is applied: all six prompts in this session **did**
carry the clone-and-grep sentence, and every agent that reported used the library rather than
fetching pages. The clause is not being ignored; it is incomplete.

[DECISION: **this extends the existing rule rather than becoming a new one.** `plan-docs`' routing
says a candidate that is a variant of a rule already present extends that rule's section — and the
admission numbers make that decisive rather than merely tidy: `config/agents-md/` currently holds
**48 `###` rules across 917 lines**, far past the ≤15 / ≤200 reference points the admission criteria
name. A 49th heading for a one-clause variant of rule 40 is the change that makes the file worse.]

## What the clause would have to say

Two halves, because they fail differently:

- **The instruction to the subagent** — one sentence in the prompt: do the work yourself, do not
  spawn subagents of your own. Cheap, and it is the whole fix for this incident.
- **The budget the caller reasons with** — six prompts is not six agents unless the prompts say so.
  This is the part that generalises: any per-agent cost estimate is a floor until nesting is ruled
  out.

## Open questions

[NEEDS CLARIFICATION: **is a blanket "never fan out" right, or should it be "say what the depth
budget is"?** Nested fan-out is sometimes correct — the gateway agent's split into per-candidate
sub-agents produced two genuinely good reports, and doing it serially would have been slower. The
failure was unbounded depth with no budget, not delegation itself. A rule that forbids it outright
is simpler to follow and loses something real; a rule that asks for a stated budget is more faithful
and is the kind of wording this repo's own adherence watch keeps finding does not land. Decide which
before writing the sentence.]

[NEEDS CLARIFICATION: **does the harness expose anything to enforce this?** The `Agent` tool takes
no `max_depth` and no aggregate agent budget, and the workflow size guideline that does exist
("under 15 agents") applies to `Workflow` scripts rather than to transitively-spawned `Agent` calls.
So today the only control is prompt text, which is exactly the shape this repo's
`[DECISION: adherence, not wording]` is sceptical of. Worth re-checking before the rule is written —
if a parameter appears, the rule becomes "pass it" and stops depending on anyone remembering.
Reported upstream from this session as a missing-capability note.]

[NEEDS CLARIFICATION: **is the failure visible enough to be worth a rule at all?** The caller learns
about nesting only when failure notifications arrive naming task-ids it never created, which is
after the budget is spent. But the user in this session counted nine failures where the session's
own transcript showed seven, and neither number could be reconciled from inside the session — so the
observability gap is real and is arguably the more useful thing to record. Cheap to establish: spawn
two agents with broad briefs and see whether anything reports the total.]

## Recommended direction

1. **Check the harness first**, per the second open question. A parameter beats a sentence, and this
   costs one look at the tool schema.
2. If there is none, **append one paragraph to `config/agents-md/research.md`'s existing
   delegated-research rule** — not a new `###` — ending on the sentence to put in the prompt rather
   than on the warning, per that fragment's own convention.
3. Do not add a second rule about budgets. The nesting sentence covers the incident; a budget rule
   with no mechanism behind it is the shape the adherence watch has measured failing five times.
