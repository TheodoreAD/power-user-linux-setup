---
status: idea
updated: 2026-08-30
repo: git@github.com:TheodoreAD/power-user-linux-setup.git
---

# Report structure for agent output

## Context

The global instructions say how agent output should _read_ — the caveman section: terse, no filler,
no decorative tables, fragments fine. They say nothing about how it should be _organised_, and the
gap shows exactly where it costs most.

Stated 2026-08-30, working through a test-framework question in a personal repo: "these reports are
hard to read, I need them to be more structured somehow… when I need to make a decision I need more
structured content to tell me what's going on, what the problems are with context, what the evidence
is, what the proposed fixes are, what their projected end states are." The message that prompted it
interleaved four different things in continuous prose — background the reader lacked, the mechanism
of a bug, the measurements proving it, and the choice being put to them. Every part was terse. The
whole was unreadable, because terseness compresses sentences and does nothing about ordering.

The same message also exposed the failure ordering causes on its own: the recommendation appeared
last, so the reader had to hold the entire argument in their head before learning what it was for.
The follow-up turned up a measurement error that inverted the recommendation — which a
recommendation-first shape would have surfaced in one line instead of at the end of a long read.

[DECISION: This is a convention about output _shape_, and it sits beside the caveman rule rather
than replacing it. Terseness governs the words inside a field; structure governs which fields exist
and in what order. They are orthogonal, and conflating them is what produced terse prose nobody
could navigate.]

## Prior art

Three established formats, converging on the same two ideas.

| source                                                    | what it contributes                                                                          |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| [BLUF / Minto Pyramid](https://untools.co/minto-pyramid/) | Answer first, then grouped support, then evidence. The reader may stop after line one.       |
| [MADR](https://adr.github.io/madr/)                       | Options are enumerated with per-option consequences — every option, not just the chosen one. |
| [Y-statements](https://adr.github.io/adr-templates/)      | A low-stakes decision compresses to one sentence. Not everything earns the full shape.       |

An [empirical comparison of ADR templates](https://arxiv.org/html/2604.27333v1) found MADR's higher
structural granularity was consistently perceived as reducing ambiguity, which is the specific
complaint here.

[DECISION: Borrow the shape, not the artifact. These are formats for documents that get committed
and reviewed; what is wanted is the same discipline applied to a terminal message that is read once.
So: the field list and the ordering, without status/date/supersedes metadata.]

## Recommended direction

Two shapes, selected by whether the reader has to _do_ anything.

**A report** — work happened, nothing is being asked:

- `Verdict` — one line. The answer.
- `Evidence` — numbers, as a table or a few bullets. Each one a measurement, not a claim.
- Detail only where it would change what the reader does next.

**A decision** — the reader chooses:

- `Recommendation` — one line, first. Which option and the half-line why.
- `Background` — only when the reader would otherwise be guessing, and marked skippable.
- `Problem` — what is wrong, with the evidence attached.
- `Options` — a table, one row per option, with what it does, what it costs, and its risk.
- `End state` — what the world looks like if the recommendation is taken.

Then the `AskUserQuestion` carries the actual choice, as it already does.

[NEEDS CLARIFICATION: Which `config/agents-md/` fragment owns this. It is closest to the caveman
rule, which lives in the collaboration/output fragment, but it is a different kind of rule — that
one is about diction and this one is about document structure. Amending that section and adding a
sibling are both defensible.]

[NEEDS CLARIFICATION: Whether the decision shape should be required whenever `AskUserQuestion` is
called, or only above some stakes threshold. Requiring it always would put a five-field preamble in
front of "commit or hold?", which is the bureaucracy objection levelled at MADR. The Y-statement
precedent says small decisions get one line — but "small" has to be defined by something a model can
apply consistently, and it is not obvious what.]

[NEEDS CLARIFICATION: Whether this reaches subagent reports. A subagent's output is relayed by the
main session rather than read directly, so the structure may belong at the relay rather than at the
source — or at both, since a structured hand-off is easier to relay faithfully.]

[DEFERRED: A worked before/after example. The session that prompted this has a real pair — the same
technical finding written as prose and then as the decision shape — and an example would carry the
rule better than the description does. It needs the messages themselves, which are not in this
file.]
