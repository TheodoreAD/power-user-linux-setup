---
status: idea
updated: 2026-09-04
---

# `~/AGENTS.md` needs a rule for how a session reports back

## Context

Filed from `repo-tasks` on 2026-09-04. The rule belongs in `~/AGENTS.md`, which is generated from
this repo's `config/agents-md/` fragments, so it has to be written here rather than in the deployed
file. Nothing in this repo was touched.

It comes from a real failure in a long session, stated by the user in their own words:

> "it's fine to make decisions without me in the loop when there's evidence, but make sure to let me
> know you made a deliberate decision, especially after saying I need to make one myself, because
> then i need to go through an entire transcript thinking i missed something"

And, asked what the reporting should look like:

> "i need the reporting to be clear across the board, with bullet points, structured. the most
> important stuff should be last. there should be a section with what you decided, and why, with a
> bit of context, and a section with what i need to decide, with more context and your proposals.
> the decisions you made are fine."

## What actually went wrong

Over one session the agent made seventeen `[DECISION: …]` entries across plans and `contributing/`
files. Three kinds were mixed together with no way to tell them apart from the prose:

1. Choices the user had actually made, correctly attributed.
2. Conclusions a measurement forced, where asking would have been theatre — an `extends` spike that
   produced `filesAnalyzed: 0, exit 0`, a licence requirement that made one design impossible on
   four of nine repos.
3. **Live trade-offs with two defensible sides, resolved by the agent and written up as settled** —
   pinning a reusable workflow to a moving ref rather than a SHA, and a judgement that moved the
   balance between options on a question the agent had _in the previous message_ told the user was
   theirs to decide.

Category 3 is the failure, and the compounding part is category 2 being indistinguishable from it in
the write-up. The user could not tell which decisions were theirs to review without reading the
diff, and the specific damage named above is re-reading a transcript to find a question they thought
they had missed.

[PITFALL: the agent asked permission at every step that _looked_ like a checkpoint — before each
commit, before each push, before adopting a dependency — so the session read as highly interactive
while the design trade-offs inside the work went unasked. Frequency of prompts is not evidence that
the right things are being surfaced, and a session can be scrupulous about the ceremony and still
decide the substance alone.]

## Open questions

[NEEDS CLARIFICATION: which fragment owns this? It is about how a session talks to the user, which
sounds like "Collaboration & output" — where the caveman-style rule and the "Ending a turn with a
next step" rule already live. But it also constrains what may be written into a repo's permanent
rationale files, which is closer to "Agent instructions & knowledge". Probably the former, with the
`[DECISION:]`-tag half cross-referenced from `plan-docs`.]

[NEEDS CLARIFICATION: does this interact with the caveman-style rule, and how? That rule says drop
articles and filler and keep fragments; this one asks for structured bullets with a bit of context
per item and more context on the open questions. They are not in conflict — terse bullets are still
terse — but the existing rule's exemption list ("security warnings, irreversible-action
confirmations") may want this added to it, since compressing a decision report is exactly where
ambiguity costs the user a transcript re-read.]

[NEEDS CLARIFICATION: should the `[DECISION:]` tag itself carry provenance? The `plan-docs`
convention defines five tags and says explicitly not to add a sixth, so a new `[AGENT-DECISION:]` is
out. But a one-clause attribution inside the existing tag — who decided, and on what — costs nothing
and is what makes a later reader able to tell category 2 from category 3. That is a `plan-docs`
change rather than an `~/AGENTS.md` one, and belongs in `agent-skills` if it is wanted.]

## Recommended direction

A rule in the collaboration fragment, roughly:

**Ending a turn that contains decisions.** Report in structured bullets, ordered least to most
important — the thing the user must act on goes last, where it is read. Two named sections:

- **What I decided, and why** — each with a clause of context and the evidence that closed it.
  Making a call on evidence is wanted; leaving the user to discover it is not.
- **What you need to decide** — more context per item, with a proposal for each rather than an open
  question. A trade-off with two defensible sides belongs here, never in the section above.

Plus the specific trap worth naming, because it is the one that cost the user real time: **having
told the user a decision is theirs, never then make it.** If new evidence changes the balance, say
that it changed and hand it back — do not record the new balance as settled.

The `[DECISION:]` half is the same rule applied to files rather than to chat: an entry in a
`contributing/` file is house policy a future agent will treat as settled, so an agent-made one says
so and names its evidence.
