---
status: idea
updated: 2026-09-27
---

# The AskUserQuestion rule went unfollowed for a whole session, and nothing on the machine can see it

## Context

`~/.agents/AGENTS.md`, "Ending a turn with a next step", says the user works only through prompts
and never types shell commands, so when the work is done and what happens next is their call — push
now, pick the next plan, stop — the concrete options go in an `AskUserQuestion` and the session acts
on the answer. Push and commit approvals are named explicitly as the case.

Measured 2026-09-27 on an `agent-skills` session, `21615ec2-5eca-4393-a831-d24275fb2551`, whose
subject was a batch of eight skill renames and which consisted almost entirely of decisions with
real trade-offs:

- **25 user turns**, 7 of them sent mid-turn, 0 `AskUserQuestion` answers.
- **0 `AskUserQuestion` tool calls**, counted from `tool_use` blocks by name.

Every decision was handed back in prose instead, and there were many: which author mark to adopt,
whether to rename the env var, whether to commit, whether to push, whether to retire the plan or
keep it, whether `research-mirror` should replace `research-trove`, whether an incidental script
defect should become its own plan. Each is exactly the shape the rule names — the user's call, with
no objectively better side — and each got a sentence ending in "say the word" or "your call" rather
than options.

**Which of the three misuse shapes: simply not followed.** The wording is clear, it was in context
the whole time, and nothing about the session's work argued against it. It did not fire, twenty-five
times. That points at measurement rather than rewording, which is the whole reason this is filed
rather than fixed.

## Evidence, and the limit of it

The certain number is the one that matters: **0 calls in a 25-turn session**, structural, from the
transcript's `tool_use` blocks.

[PITFALL: **the accompanying claim — "asked in prose every time" — was an impression, and the probe
written to quantify it was also wrong.** A script counting assistant turns whose final text ends in
a question mark and which are followed by a user turn returned **2**. Both numbers are wrong for the
question: the rule is about handing a decision back, and a handoff does not need a question mark —
"Give me the env var answer and I'll go" and "Tell me when the push is through and I'll do the
retirement" are the shape, and neither ends in one. So the frequency is genuinely unmeasured here,
and picking either 2 or "every time" would have written a wrong number into a durable file. The
instances above were established by reading the conversation, not counted.]

**Nothing on this machine measures tool choice.** `session-bash-audit` reads Bash calls and tags
command shapes; a rule about which _tool_ an agent reaches for is invisible to it, and to every
other instrument here. So unlike the Bash rules — where a rate can be compared against a baseline
and a regression seen — this rule's adherence is only ever established by a human noticing its
absence, which is what happened: the session's own harvest reported the zero, decided not to file
it, and the user asked why.

## Open questions

[NEEDS CLARIFICATION: is this a rule-wording problem or a measurement gap? The rule is not
ambiguous, so rewording has nothing to fix. What is missing is any signal: an agent that never
reaches for the tool gets no feedback, and a session can end having handed back a dozen decisions in
prose while reporting that it followed its instructions. A count of `AskUserQuestion` calls per
session against user-turn count is one line in a transcript reader and would make the rate visible —
but it belongs in whichever instrument owns tool-level adherence, and today none does.]

[NEEDS CLARIFICATION: does the prose form actually cost anything here? It worked — the user answered
every prose question and the session never stalled. Two candidate costs, neither measured: a prose
question can be missed in a long report, where the tool's options are unmissable; and the tool
records the answer as a first-class turn, which is what `session-harvest`'s `turns` extraction
reads, so a decision made in prose is harder for a later session to recover. Against: forcing the
tool onto every "shall I commit?" is the bureaucracy objection, and the rule's own wording is about
the case where work is _done_ rather than every exchange.]

[NEEDS CLARIFICATION: this falsifies a premise of
`plans/2026-08-30-report-structure-for-agent-output.md` in this repo, which designs the decision
shape that should accompany a call and says the `AskUserQuestion` "carries the actual choice, as it
already does". On this session's evidence it does not — there were no calls to carry anything. Worth
deciding together with that plan rather than separately.]

## Recommended direction

Decide the measurement question first, since the rule needs no rewording. If a count is wanted, the
cheapest honest version is per-session: `AskUserQuestion` calls against user turns, printed beside
the Bash adherence rates a harvest already reports, so a zero in a decision-heavy session is visible
in the same place as a `head`/`tail` rate. Then read it against this plan's second question before
treating a low number as a fault — the prose form may be fine, and the point of measuring is to find
out rather than to enforce.
